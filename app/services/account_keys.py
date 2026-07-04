import hashlib
import secrets
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


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def init_account_keys_db():
    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS account_api_keys (
                    key_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    label TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    last_used_at REAL
                )
                """
            )

            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(account_api_keys)").fetchall()
            }

            if "key_id" not in cols:
                conn.execute("ALTER TABLE account_api_keys ADD COLUMN key_id TEXT")

            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_account_api_keys_key_id ON account_api_keys(key_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_account_api_keys_account_id ON account_api_keys(account_id)"
            )

            rows = conn.execute(
                """
                SELECT key_hash
                FROM account_api_keys
                WHERE key_id IS NULL OR key_id = ''
                """
            ).fetchall()

            for row in rows:
                conn.execute(
                    """
                    UPDATE account_api_keys
                    SET key_id = ?
                    WHERE key_hash = ?
                    """,
                    ("key_" + secrets.token_urlsafe(10), row["key_hash"]),
                )

            conn.commit()
        finally:
            conn.close()


def create_account_api_key(account_id: str, label: str | None = None) -> dict[str, Any]:
    init_account_keys_db()

    api_key = "symon_user_" + secrets.token_urlsafe(32)
    key_hash = hash_key(api_key)
    key_id = "key_" + secrets.token_urlsafe(10)
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO account_api_keys (
                    key_hash, key_id, account_id, label, is_active, created_at
                )
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (key_hash, key_id, account_id, label, now),
            )
            conn.commit()
        finally:
            conn.close()

    return {
        "api_key": api_key,
        "key_id": key_id,
        "account_id": account_id,
        "label": label,
    }


def lookup_account_by_api_key(api_key: str) -> dict[str, Any] | None:
    init_account_keys_db()

    key_hash = hash_key(api_key)
    now = time.time()

    with _LOCK:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT key_hash, key_id, account_id, label, is_active, created_at, last_used_at
                FROM account_api_keys
                WHERE key_hash = ?
                """,
                (key_hash,),
            ).fetchone()

            if not row or not row["is_active"]:
                return None

            conn.execute(
                """
                UPDATE account_api_keys
                SET last_used_at = ?
                WHERE key_hash = ?
                """,
                (now, key_hash),
            )
            conn.commit()

            return dict(row)
        finally:
            conn.close()


def list_account_api_keys(account_id: str | None = None) -> list[dict[str, Any]]:
    init_account_keys_db()

    with _LOCK:
        conn = connect()
        try:
            if account_id:
                rows = conn.execute(
                    """
                    SELECT key_id, account_id, label, is_active, created_at, last_used_at
                    FROM account_api_keys
                    WHERE account_id = ?
                    ORDER BY created_at DESC
                    """,
                    (account_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT key_id, account_id, label, is_active, created_at, last_used_at
                    FROM account_api_keys
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                ).fetchall()

            return [dict(row) for row in rows]
        finally:
            conn.close()


def deactivate_account_api_key_id(key_id: str) -> bool:
    init_account_keys_db()

    with _LOCK:
        conn = connect()
        try:
            cur = conn.execute(
                """
                UPDATE account_api_keys
                SET is_active = 0
                WHERE key_id = ?
                """,
                (key_id,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def deactivate_account_api_key(api_key: str) -> bool:
    init_account_keys_db()

    key_hash = hash_key(api_key)

    with _LOCK:
        conn = connect()
        try:
            cur = conn.execute(
                """
                UPDATE account_api_keys
                SET is_active = 0
                WHERE key_hash = ?
                """,
                (key_hash,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
