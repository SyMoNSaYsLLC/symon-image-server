import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

DB_PATH = Path("/home/google/symon-image-server/data/symon_jobs.sqlite3")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_LOCK = threading.Lock()


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS image_jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    seconds REAL,
                    filename TEXT,
                    url TEXT,
                    error TEXT,
                    job_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_image_jobs_created_at ON image_jobs(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_image_jobs_status ON image_jobs(status)")
            conn.commit()
        finally:
            conn.close()


def save_job(job: dict[str, Any]):
    init_db()

    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO image_jobs (
                    job_id, status, mode, prompt, created_at,
                    started_at, finished_at, seconds,
                    filename, url, error, job_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    mode=excluded.mode,
                    prompt=excluded.prompt,
                    created_at=excluded.created_at,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    seconds=excluded.seconds,
                    filename=excluded.filename,
                    url=excluded.url,
                    error=excluded.error,
                    job_json=excluded.job_json
                """,
                (
                    job["job_id"],
                    job.get("status", "unknown"),
                    job.get("mode", "fast"),
                    job.get("prompt", ""),
                    job.get("created_at"),
                    job.get("started_at"),
                    job.get("finished_at"),
                    job.get("seconds"),
                    job.get("filename"),
                    job.get("url"),
                    job.get("error"),
                    json.dumps(job),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def get_job_db(job_id: str) -> dict[str, Any] | None:
    init_db()

    with _LOCK:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT job_json FROM image_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["job_json"])
        finally:
            conn.close()


def list_jobs_db(limit: int = 100) -> list[dict[str, Any]]:
    init_db()

    with _LOCK:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT job_json
                FROM image_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [json.loads(row["job_json"]) for row in rows]
        finally:
            conn.close()


def load_recent_jobs(limit: int = 100) -> dict[str, dict[str, Any]]:
    jobs = {}
    for job in list_jobs_db(limit=limit):
        if job.get("status") in {"queued", "running"}:
            job["status"] = "interrupted"
            job["error"] = "Server restarted before this job finished."
            save_job(job)
        jobs[job["job_id"]] = job
    return jobs
