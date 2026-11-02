#!/usr/bin/env python3
"""
Small CLI for updating application status and checking stale follow-ups.

Usage:
  python3 track.py list [status]          # list jobs, optionally filtered
  python3 track.py apply <job_id> [days]  # mark applied, set follow-up N days out (default 7)
  python3 track.py status <job_id> <new_status> [notes]
  python3 track.py followups              # show applications due a follow-up
"""
import sys
from datetime import datetime, timedelta
from db import get_conn, set_status, stale_follow_ups


def list_jobs(status_filter=None):
    conn = get_conn()
    q = "SELECT id, title, company, status, first_seen FROM jobs"
    params = ()
    if status_filter:
        q += " WHERE status = ?"
        params = (status_filter,)
    q += " ORDER BY first_seen DESC LIMIT 50"
    for row in conn.execute(q, params):
        print(f"{row[0]:20} [{row[3]:12}] {row[1]} — {row[2]} (seen {row[4][:10]})")


def mark_applied(job_id, days=7):
    conn = get_conn()
    today = datetime.now().date()
    follow_up = (today + timedelta(days=int(days))).isoformat()
    set_status(conn, job_id, "applied", applied_date=today.isoformat(),
               follow_up_date=follow_up)
    print(f"Marked {job_id} as applied. Follow up on {follow_up}.")


def update_status(job_id, new_status, notes=None):
    conn = get_conn()
    set_status(conn, job_id, new_status, notes=notes)
    print(f"Updated {job_id} -> {new_status}")


def show_followups():
    conn = get_conn()
    rows = stale_follow_ups(conn)
    if not rows:
        print("No follow-ups due.")
        return
    for job_id, title, company, due in rows:
        print(f"DUE {due}: {title} — {company} ({job_id})")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == "list":
        list_jobs(args[1] if len(args) > 1 else None)
    elif cmd == "apply":
        mark_applied(args[1], args[2] if len(args) > 2 else 7)
    elif cmd == "status":
        update_status(args[1], args[2], args[3] if len(args) > 3 else None)
    elif cmd == "followups":
        show_followups()
    else:
        print(__doc__)
