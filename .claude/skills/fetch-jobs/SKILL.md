---
name: fetch-jobs
description: Run the JobHunter fetcher to pull new listings into jobs.db and write today's digest. Use when the user asks to run the fetcher, fetch jobs, or update the job database.
allowed-tools: Bash(set -a && source .env && set +a && /usr/bin/python3 fetch_jobs.py*), Bash(sqlite3 jobs.db *)
---

Run the job fetcher from the project root (the folder containing `fetch_jobs.py`).

1. Run it with `.env` loaded (the systemd service loads it via EnvironmentFile; a plain shell does not):

   ```
   set -a && source .env && set +a && /usr/bin/python3 fetch_jobs.py 2>&1 | tail -40
   ```

   Always use `/usr/bin/python3` — the bare `python3` on this machine lacks `requests`/`pyyaml`.

2. Show the database totals by status:

   ```
   sqlite3 jobs.db "select status, count(*) from jobs group by 1"
   ```

3. Report briefly: how many new matches were found, the per-status totals, the digest path (`digests/YYYY-MM-DD.md`), and any errors or skipped steps (e.g. missing Reed key, email skipped, API rate limits). If the run failed, show the error output.
