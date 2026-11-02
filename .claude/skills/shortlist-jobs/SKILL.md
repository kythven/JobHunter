---
name: shortlist-jobs
description: Pull the best-fit jobs from jobs.db that the user hasn't applied to yet and present them as a ranked markdown table. Use when the user asks for a shortlist, the best/top jobs, jobs that fit their CV, or what to apply for next.
allowed-tools: Bash(sqlite3 jobs.db *)
---

Work from the project root (the folder containing `fetch_jobs.py`). Arguments (optional): the number of jobs (default 10) and a role type (default `dev`).

## 1. Know the CV

Use the CV summary in memory (`dev-cv` for developer roles). Don't reread the .docx unless the file is newer than the memory says. For a role type with no memory yet (e.g. CRM, CySec), read that CV from `~/Downloads/Downloaded Documents/MyCVs/`, save a summary to memory the same way, and then continue.

## 2. Query candidates. Only status `new`, never anything already actioned

```
sqlite3 -separator ' | ' jobs.db "select id,title,company,location,salary,url from jobs where status='new' and (<title filters for the role type>)"
```

Also exclude near-duplicates of jobs already applied to (the same role reposted by a different agency, or by the same company under a slightly different title):

```
sqlite3 -separator ' | ' jobs.db "select title,company,location from jobs where status!='new'"
```

For developer roles, drop:
- senior, lead, principal, staff, head, architect and VP roles
- stacks that are mainly Java, .NET/C#, Angular, Salesforce or Dynamics
- security-clearance or defence roles
- "Placement Programme / No experience needed" listings (these are paid training schemes)
- London roles paying £100k+ (these are contract day rates converted to a yearly figure)
- security, CRM and pen-test roles (those belong to the other CVs)

## 3. Rank

In order:
1. Stack overlap with the CV (PHP/JS, Python, Node, API/integration/automation work score highest).
2. Distance from Cardiff: Cardiff/Newport, then Bristol/Bath, then London. Remote counts as Cardiff.
3. Hiring directly beats going through an agency.
4. Salary: the user will take anything ≥ £24k, so use salary only to break ties.

Pick only one listing per underlying role. If several agencies post the same Bristol PHP job, list the best one and mention in its row that it may overlap with others.

## 4. Present

A markdown table with the title linked to its URL:

| # | Role | Company | Location | Salary | Why it fits |
|---|---|---|---|---|---|
| 1 | [Title](url) | Company | Town | £X–Yk | short reason tied to the CV |

Keep the job `id` for each row (don't show it) so the apply step can update status.

Then add:
- **What I left out:** a short list of the notable exclusions and why.
- **Caveat:** the DB stores titles, not full descriptions, so the actual requirements get checked when each listing is opened to apply.

## 5. Tracking

Once an application is confirmed as submitted (the site shows a confirmation page or message), mark it in the DB:

```
sqlite3 jobs.db "update jobs set status='applied', applied_date=date('now'), follow_up_date=date('now','+7 days'), notes='<CV used; anything notable>' where id='<id>'"
```

If a listing is dead, a scam or a clear mismatch on inspection, set `status='ignored'` with a reason in `notes` so it never comes back. Never mark a job `applied` unless the submission actually went through.
