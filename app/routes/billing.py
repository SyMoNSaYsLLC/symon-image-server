import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services.auth import require_api_key
from app.services.payment_db import (
    get_balance,
    ledger,
    record_stripe_session,
    complete_stripe_session_once,
    add_credits,
)

load_dotenv()

router = APIRouter(prefix="/billing", tags=["billing"])

CREDIT_PACKS = {
    "starter": {
        "name": "Starter Pack",
        "credits": 100,
        "amount_cents": 500,
    },
    "creator": {
        "name": "Creator Pack",
        "credits": 500,
        "amount_cents": 2000,
    },
    "pro": {
        "name": "Pro Pack",
        "credits": 1500,
        "amount_cents": 5000,
    },
}


class CheckoutRequest(BaseModel):
    account_id: str
    pack: str = "starter"


@router.get("/packs")
def packs():
    return {
        "ok": True,
        "packs": CREDIT_PACKS,
    }


@router.get("/balance/{account_id}")
def balance(account_id: str, _auth: bool = Depends(require_api_key)):
    return {
        "ok": True,
        "account_id": account_id,
        "credits": get_balance(account_id),
        "ledger": ledger(account_id, limit=20),
    }


@router.post("/checkout")
def create_checkout(req: CheckoutRequest, _auth: bool = Depends(require_api_key)):
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8090")

    if not stripe_secret_key:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_SECRET_KEY is not configured",
        )

    if req.pack not in CREDIT_PACKS:
        raise HTTPException(status_code=400, detail="invalid credit pack")

    pack = CREDIT_PACKS[req.pack]
    stripe.api_key = stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=req.account_id,
        success_url=f"{public_base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{public_base_url}/billing/cancel",
        metadata={
            "account_id": req.account_id,
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
        account_id=req.account_id,
        pack=req.pack,
        credits=pack["credits"],
        amount_cents=pack["amount_cents"],
        status="created",
    )

    return {
        "ok": True,
        "checkout_session_id": session.id,
        "checkout_url": session.url,
        "account_id": req.account_id,
        "pack": req.pack,
        "credits": pack["credits"],
        "amount_cents": pack["amount_cents"],
    }


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not stripe_secret_key or not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook is not configured")

    stripe.api_key = stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]

        result = complete_stripe_session_once(session_id)

        if result.get("ok") and not result.get("already_completed"):
            add_credits(
                result["account_id"],
                int(result["credits"]),
                reason="stripe_checkout_completed",
                ref_id=session_id,
            )

    return {
        "ok": True,
        "received": True,
        "event_type": event["type"],
    }


@router.get("/success")
def success(session_id: str | None = None):
    return {
        "ok": True,
        "status": "payment_success_redirect",
        "session_id": session_id,
    }


@router.get("/cancel")
def cancel():
    return {
        "ok": False,
        "status": "payment_cancelled",
    }
