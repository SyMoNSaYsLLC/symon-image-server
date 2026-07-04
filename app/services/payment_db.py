import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

DB_PATH = Path("/home/google/symon-image-server/data/symon_jobs.sqlite3")
_LOCK = threading.Lock()


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_payment_db():
    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    credits INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS credit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    ref_id TEXT,
                    created_at REAL NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stripe_sessions (
                    stripe_session_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    pack TEXT NOT NULL,
                    credits INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    completed_at REAL
                )
                """
            )

            conn.commit()
        finally:
            conn.close()


def ensure_account(account_id: str):
    init_payment_db()
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO accounts (account_id, credits, created_at, updated_at)
                VALUES (?, 0, ?, ?)
                ON CONFLICT(account_id) DO NOTHING
                """,
                (account_id, now, now),
            )
            conn.commit()
        finally:
            conn.close()


def get_balance(account_id: str) -> int:
    ensure_account(account_id)

    with _LOCK:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT credits FROM accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            return int(row["credits"]) if row else 0
        finally:
            conn.close()


def add_credits(account_id: str, credits: int, reason: str, ref_id: str | None = None):
    ensure_account(account_id)
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE accounts
                SET credits = credits + ?, updated_at = ?
                WHERE account_id = ?
                """,
                (credits, now, account_id),
            )

            conn.execute(
                """
                INSERT INTO credit_ledger (account_id, delta, reason, ref_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (account_id, credits, reason, ref_id, now),
            )

            conn.commit()
        finally:
            conn.close()


def spend_credits(account_id: str, credits: int, reason: str, ref_id: str | None = None) -> bool:
    ensure_account(account_id)
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT credits FROM accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()

            current = int(row["credits"]) if row else 0
            if current < credits:
                return False

            conn.execute(
                """
                UPDATE accounts
                SET credits = credits - ?, updated_at = ?
                WHERE account_id = ?
                """,
                (credits, now, account_id),
            )

            conn.execute(
                """
                INSERT INTO credit_ledger (account_id, delta, reason, ref_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (account_id, -credits, reason, ref_id, now),
            )

            conn.commit()
            return True
        finally:
            conn.close()


def record_stripe_session(
    stripe_session_id: str,
    account_id: str,
    pack: str,
    credits: int,
    amount_cents: int,
    status: str,
):
    init_payment_db()
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO stripe_sessions (
                    stripe_session_id, account_id, pack, credits,
                    amount_cents, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stripe_session_id) DO NOTHING
                """,
                (
                    stripe_session_id,
                    account_id,
                    pack,
                    credits,
                    amount_cents,
                    status,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def complete_stripe_session_once(stripe_session_id: str) -> dict[str, Any]:
    init_payment_db()
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT *
                FROM stripe_sessions
                WHERE stripe_session_id = ?
                """,
                (stripe_session_id,),
            ).fetchone()

            if not row:
                return {"ok": False, "reason": "session_not_found"}

            if row["status"] == "completed":
                return {
                    "ok": True,
                    "already_completed": True,
                    "account_id": row["account_id"],
                    "credits": row["credits"],
                }

            conn.execute(
                """
                UPDATE stripe_sessions
                SET status = 'completed', completed_at = ?
                WHERE stripe_session_id = ?
                """,
                (now, stripe_session_id),
            )

            conn.commit()

            return {
                "ok": True,
                "already_completed": False,
                "account_id": row["account_id"],
                "credits": int(row["credits"]),
            }
        finally:
            conn.close()


def ledger(account_id: str, limit: int = 50):
    ensure_account(account_id)

    with _LOCK:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT account_id, delta, reason, ref_id, created_at
                FROM credit_ledger
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()

            return [dict(row) for row in rows]
        finally:
            conn.close()
