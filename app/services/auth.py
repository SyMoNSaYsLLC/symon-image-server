import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv

from app.services.account_keys import lookup_account_by_api_key

load_dotenv()


def get_admin_api_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def require_api_key(x_api_key: str | None = Header(default=None)):
    """
    Admin/server API key from .env.
    Used for admin, billing balance, and protected management routes.
    """
    keys = get_admin_api_keys()

    if not keys:
        raise HTTPException(status_code=500, detail="admin API key auth is not configured")

    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=401, detail="invalid or missing API key")

    return True


def require_account_api_key(x_api_key: str | None = Header(default=None)) -> dict:
    """
    User/account API key from SQLite.
    Used for spending credits and submitting image jobs.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing account API key")

    account = lookup_account_by_api_key(x_api_key)

    if not account:
        raise HTTPException(status_code=401, detail="invalid account API key")

    return account
