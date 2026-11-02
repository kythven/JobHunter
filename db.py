"""SQLite storage for seen jobs and application tracking."""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,        -- source:external_id, e.g. "adzuna:12345"
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary TEXT,
    url TEXT NOT NULL,
    first_seen TEXT NOT NULL,   -- ISO timestamp
    status TEXT DEFAULT 'new',  -- new | applied | interviewing | rejected | offer | ignored
    applied_date TEXT,
    follow_up_date TEXT,
    notes TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def is_new(conn, job_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row is None


def insert_job(conn, job: dict):
    conn.execute(
        """INSERT OR IGNORE INTO jobs
           (id, source, title, company, location, salary, url, first_seen, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
        (
            job["id"], job["source"], job["title"], job.get("company"),
            job.get("location"), job.get("salary"), job["url"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()


def set_status(conn, job_id: str, status: str, notes: str = None,
                applied_date: str = None, follow_up_date: str = None):
    fields, params = ["status = ?"], [status]
    if notes is not None:
        fields.append("notes = ?"); params.append(notes)
    if applied_date is not None:
        fields.append("applied_date = ?"); params.append(applied_date)
    if follow_up_date is not None:
        fields.append("follow_up_date = ?"); params.append(follow_up_date)
    params.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()


def stale_follow_ups(conn):
    """Applications with a follow_up_date in the past that are still open."""
    today = datetime.now().date().isoformat()
    return conn.execute(
        """SELECT id, title, company, follow_up_date FROM jobs
           WHERE status = 'applied' AND follow_up_date IS NOT NULL
           AND follow_up_date <= ?""",
        (today,),
    ).fetchall()
