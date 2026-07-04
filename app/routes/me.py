import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services.auth import require_account_api_key
from app.services.payment_db import get_balance, ledger, record_stripe_session
from app.services.job_db import list_jobs_db, get_job_db
from app.routes.billing import CREDIT_PACKS

load_dotenv()

router = APIRouter(prefix="/me", tags=["me"])


class MeCheckoutRequest(BaseModel):
    pack: str = "starter"


def public_job(job: dict):
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "mode": job.get("mode"),
        "seconds": job.get("seconds"),
        "url": job.get("url"),
        "credit_cost": job.get("credit_cost"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "error": job.get("error"),
    }


def my_jobs_for(account_id: str, limit: int = 100):
    all_jobs = list_jobs_db(limit=limit)
    return [
        public_job(job)
        for job in all_jobs
        if job.get("account_id") == account_id
    ]


@router.get("")
def me(account: dict = Depends(require_account_api_key)):
    account_id = account["account_id"]

    return {
        "ok": True,
        "account_id": account_id,
        "credits": get_balance(account_id),
        "api_key": {
            "key_id": account.get("key_id"),
            "label": account.get("label"),
        },
        "recent_jobs": my_jobs_for(account_id, limit=100)[:20],
        "recent_ledger": ledger(account_id, limit=20),
    }


@router.get("/jobs")
def my_jobs(account: dict = Depends(require_account_api_key)):
    account_id = account["account_id"]

    return {
        "ok": True,
        "account_id": account_id,
        "jobs": my_jobs_for(account_id, limit=100),
    }


@router.get("/jobs/{job_id}")
def my_job(job_id: str, account: dict = Depends(require_account_api_key)):
    account_id = account["account_id"]
    job = get_job_db(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if job.get("account_id") != account_id:
        raise HTTPException(status_code=404, detail="job not found")

    return {
        "ok": True,
        "account_id": account_id,
        "job": public_job(job),
    }


@router.post("/checkout")
def me_checkout(req: MeCheckoutRequest, account: dict = Depends(require_account_api_key)):
    account_id = account["account_id"]

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8090")

    if not stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is not configured")

    if req.pack not in CREDIT_PACKS:
        raise HTTPException(status_code=400, detail="invalid credit pack")

    pack = CREDIT_PACKS[req.pack]
    stripe.api_key = stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=account_id,
        success_url=f"{public_base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{public_base_url}/billing/cancel",
        metadata={
            "account_id": account_id,
            "pack": req.pack,
            "credits": str(pack["credits"]),
        },
        line_items=[
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": pack["amount_cents"],
                    "product_data": {
                        "name": f"Symon Image Credits - {pack['name']}",
                        "description": f"{pack['credits']} image generation credits",
                    },
                },
            }
        ],
    )

    record_stripe_session(
        stripe_session_id=session.id,
        account_id=account_id,
        pack=req.pack,
        credits=pack["credits"],
        amount_cents=pack["amount_cents"],
        status="created",
    )

    return {
        "ok": True,
        "checkout_session_id": session.id,
        "checkout_url": session.url,
        "account_id": account_id,
        "pack": req.pack,
        "credits": pack["credits"],
        "amount_cents": pack["amount_cents"],
    }
