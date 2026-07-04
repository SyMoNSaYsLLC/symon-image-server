from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth import require_api_key
from app.services.account_keys import (
    create_account_api_key,
    list_account_api_keys,
    deactivate_account_api_key_id,
)
from app.services.payment_db import get_balance, ledger

router = APIRouter(prefix="/accounts", tags=["accounts"])


class CreateKeyRequest(BaseModel):
    label: str | None = None


@router.post("/{account_id}/keys")
def create_key(
    account_id: str,
    req: CreateKeyRequest,
    _auth: bool = Depends(require_api_key),
):
    created = create_account_api_key(account_id, req.label)

    return {
        "ok": True,
        "account_id": account_id,
        "key_id": created["key_id"],
        "api_key": created["api_key"],
        "label": created["label"],
        "warning": "Store this api_key now. It will not be shown again.",
    }


@router.get("/{account_id}/keys")
def list_keys(account_id: str, _auth: bool = Depends(require_api_key)):
    return {
        "ok": True,
        "account_id": account_id,
        "keys": list_account_api_keys(account_id),
    }


@router.delete("/keys/{key_id}")
def revoke_key(key_id: str, _auth: bool = Depends(require_api_key)):
    ok = deactivate_account_api_key_id(key_id)

    if not ok:
        raise HTTPException(status_code=404, detail="key not found")

    return {
        "ok": True,
        "key_id": key_id,
        "status": "revoked",
    }


@router.get("/{account_id}")
def account_status(account_id: str, _auth: bool = Depends(require_api_key)):
    return {
        "ok": True,
        "account_id": account_id,
        "credits": get_balance(account_id),
        "keys": list_account_api_keys(account_id),
        "ledger": ledger(account_id, limit=20),
    }
