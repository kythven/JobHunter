#!/usr/bin/env python3
"""
Pull UK dev job listings from Adzuna + Reed, filter against config.yaml,
dedup against jobs.db, and write today's new matches to a markdown digest.

Setup:
  1. pip install requests pyyaml --break-system-packages
  2. Get free API credentials:
       Adzuna: https://developer.adzuna.com/  (app_id + app_key)
       Reed:   https://www.reed.co.uk/developers/jobseeker  (api key only)
  3. Export as env vars (or put in a .env and source it):
       export ADZUNA_APP_ID=...
       export ADZUNA_APP_KEY=...
       export REED_API_KEY=...
  4. Run: python3 fetch_jobs.py
"""
import os
import sys
import yaml
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db import get_conn, is_new, insert_job
from summarize import clean_description
from mailer import send_digest_email

CONFIG = yaml.safe_load(open(Path(__file__).parent / "config.yaml"))
DIGEST_DIR = Path(__file__).parent / "digests"
DIGEST_DIR.mkdir(exist_ok=True)

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
REED_API_KEY = os.environ.get("REED_API_KEY")


def title_excluded(title: str) -> bool:
    t = title.lower()
    return any(bad.lower() in t for bad in CONFIG.get("exclude_title_contains", []))


def fetch_adzuna(keyword: str, location: str):
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        return []
    url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": keyword,
        "where": location,
        "distance": CONFIG.get("distance_miles", 25),
        "results_per_page": CONFIG.get("results_per_source", 50),
        "salary_min": CONFIG.get("salary_min", 0) or None,
        "content-type": "application/json",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"[adzuna] error for '{keyword}' in '{location}': {e}", file=sys.stderr)
        return []

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "id": f"adzuna:{item['id']}",
            "source": "adzuna",
            "title": item.get("title", "").strip(),
            "company": (item.get("company") or {}).get("display_name"),
            "location": (item.get("location") or {}).get("display_name"),
            "salary": _adzuna_salary(item),
            "url": item.get("redirect_url"),
            "description": item.get("description", ""),
        })
    return jobs


def _adzuna_salary(item):
    lo, hi = item.get("salary_min"), item.get("salary_max")
    if lo and hi:
        return f"£{int(lo):,} - £{int(hi):,}"
    return None


def fetch_reed(keyword: str, location: str):
    if not REED_API_KEY:
        return []
    url = "https://www.reed.co.uk/api/1.0/search"
    params = {
        "keywords": keyword,
        "locationName": location,
        "distanceFromLocation": CONFIG.get("distance_miles", 25),
        "resultsToTake": CONFIG.get("results_per_source", 50),
        "minimumSalary": CONFIG.get("salary_min", 0) or None,
    }
    try:
        r = requests.get(url, params=params, auth=(REED_API_KEY, ""), timeout=20)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"[reed] error for '{keyword}' in '{location}': {e}", file=sys.stderr)
        return []

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "id": f"reed:{item['jobId']}",
            "source": "reed",
            "title": item.get("jobTitle", "").strip(),
            "company": item.get("employerName"),
            "location": item.get("locationName"),
            "salary": _reed_salary(item),
            "url": item.get("jobUrl"),
            "description": item.get("jobDescription", ""),
        })
    return jobs


def _reed_salary(item):
    lo, hi = item.get("minimumSalary"), item.get("maximumSalary")
    if lo and hi:
        return f"£{int(lo):,} - £{int(hi):,}"
    return None


def main():
    if not any([ADZUNA_APP_ID and ADZUNA_APP_KEY, REED_API_KEY]):
        print("No API credentials set. See the setup notes at the top of this "
              "file — you need at least one of Adzuna or Reed configured.",
              file=sys.stderr)
        sys.exit(1)

    conn = get_conn()
    new_jobs = []

    locations = CONFIG.get("locations", ["UK"])

    for kw in CONFIG.get("keywords", []):
        for loc in locations:
            print(f"Searching '{kw}' in '{loc}'...")
            results = fetch_adzuna(kw, loc) + fetch_reed(kw, loc)
            for job in results:
                if not job.get("title") or not job.get("url"):
                    continue
                if title_excluded(job["title"]):
                    continue
                if is_new(conn, job["id"]):
                    insert_job(conn, job)
                    new_jobs.append(job)

    body, match_count = write_digest(new_jobs)
    print(f"Done. {len(new_jobs)} new matches written to digest.")

    if match_count:
        today = datetime.now().strftime("%Y-%m-%d")
        send_digest_email(f"Job digest — {today} ({match_count} new)", body)


def write_digest(jobs):
    today = datetime.now().strftime("%Y-%m-%d")
    path = DIGEST_DIR / f"{today}.md"
    lines = [f"# Job digest — {today}", ""]
    match_count = 0
    if not jobs:
        lines.append("No new matches today.")
    else:
        # de-dupe title+company pairs across sources for readability
        seen = set()
        for j in jobs:
            key = (j["title"].lower(), (j["company"] or "").lower())
            if key in seen:
                continue
            seen.add(key)
            match_count += 1
            lines.append(f"## {j['title']}")
            lines.append(f"- **Company:** {j.get('company') or 'n/a'}")
            lines.append(f"- **Location:** {j.get('location') or 'n/a'}")
            lines.append(f"- **Salary:** {j.get('salary') or 'n/a'}")
            lines.append(f"- **Source:** {j['source']}")
            lines.append(f"- **Link:** {j['url']}")
            desc = clean_description(j.get("description", ""))
            if desc:
                lines.append(f"- **Description:** {desc}")
            lines.append("")
    body = "\n".join(lines)
    path.write_text(body, encoding="utf-8")
    print(f"Digest written to {path}")
    return body, match_count


if __name__ == "__main__":
    main()
