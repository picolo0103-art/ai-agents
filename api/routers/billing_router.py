"""Stripe billing — checkout session, customer portal, webhook."""
import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database.crud import (get_tenant, get_tenant_by_stripe_customer,
                            update_tenant_subscription)
from database.database import get_db
from database.models import User

logger = logging.getLogger("agentai.billing")

router = APIRouter(prefix="/billing", tags=["billing"])

# ── Stripe config ─────────────────────────────────────────────────────────────

STRIPE_SECRET_KEY     = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRICE_PRO      = os.getenv("STRIPE_PRICE_PRO", "").strip()
STRIPE_PRICE_ENT      = os.getenv("STRIPE_PRICE_ENTERPRISE", "").strip()
APP_URL               = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# price_id → plan name (built at startup from env vars)
PLAN_BY_PRICE: dict[str, str] = {}
if STRIPE_PRICE_PRO: PLAN_BY_PRICE[STRIPE_PRICE_PRO] = "pro"
if STRIPE_PRICE_ENT: PLAN_BY_PRICE[STRIPE_PRICE_ENT] = "enterprise"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_stripe():
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe non configuré — contactez le support")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def billing_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current plan info for the authenticated tenant."""
    t = get_tenant(db, user.tenant_id)
    plan   = (t.plan or "free") if t else "free"
    limit  = 100 if plan == "free" else None
    return {
        "plan":                t.plan               if t else "free",
        "subscription_status": t.subscription_status if t else "inactive",
        "messages_this_month": t.messages_this_month if t else 0,
        "messages_limit":      limit,
        "stripe_configured":   bool(STRIPE_SECRET_KEY),
    }


@router.post("/checkout")
def create_checkout(
    plan: str = Query(..., regex="^(pro|enterprise)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout Session and return the redirect URL."""
    _require_stripe()

    price_id = STRIPE_PRICE_PRO if plan == "pro" else STRIPE_PRICE_ENT
    if not price_id:
        raise HTTPException(503, f"Prix Stripe pour le plan '{plan}' non configuré")

    tenant      = get_tenant(db, user.tenant_id)
    customer_id: Optional[str] = tenant.stripe_customer_id if tenant else None

    session = stripe.checkout.Session.create(
        customer=customer_id or None,
        customer_email=None if customer_id else user.email,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{APP_URL}/dashboard?checkout=success",
        cancel_url=f"{APP_URL}/dashboard?checkout=canceled",
        metadata={"tenant_id": user.tenant_id},
        subscription_data={"trial_period_days": 14},
        allow_promotion_codes=True,
    )
    logger.info("Checkout session created: tenant=%s plan=%s", user.tenant_id, plan)
    return {"checkout_url": session.url}


@router.post("/portal")
def customer_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session (manage subscription, invoices)."""
    _require_stripe()

    tenant = get_tenant(db, user.tenant_id)
    if not tenant or not tenant.stripe_customer_id:
        raise HTTPException(400, "Aucun abonnement actif — abonnez-vous d'abord")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=f"{APP_URL}/dashboard",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe sends events here (POST with raw body + Stripe-Signature header).
    Signature is verified before any processing.
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "Webhook secret non configuré")

    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(400, "Invalid signature")
    except Exception as exc:
        logger.error("Stripe webhook parse error: %s", exc)
        raise HTTPException(400, "Bad payload")

    _handle_stripe_event(db, event)
    return {"status": "ok"}


# ── Event handlers ────────────────────────────────────────────────────────────

def _handle_stripe_event(db: Session, event: dict):
    etype = event["type"]
    obj   = event["data"]["object"]
    logger.info("Stripe event: %s", etype)

    if etype == "checkout.session.completed":
        _on_checkout_completed(db, obj)

    elif etype in ("customer.subscription.created", "customer.subscription.updated"):
        _on_subscription_change(db, obj)

    elif etype == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        tenant = get_tenant_by_stripe_customer(db, customer_id)
        if tenant:
            update_tenant_subscription(
                db, tenant.id, plan="free", subscription_status="canceled",
            )
            logger.info("Subscription canceled → free: tenant=%s", tenant.id)

    elif etype == "invoice.payment_failed":
        customer_id = obj.get("customer")
        tenant = get_tenant_by_stripe_customer(db, customer_id)
        if tenant:
            update_tenant_subscription(
                db, tenant.id, plan=tenant.plan or "free",
                subscription_status="past_due",
            )
            logger.warning("Payment failed: tenant=%s", tenant.id)


def _on_checkout_completed(db: Session, obj: dict):
    tenant_id       = obj.get("metadata", {}).get("tenant_id")
    customer_id     = obj.get("customer")
    subscription_id = obj.get("subscription")
    plan            = "pro"  # default

    if subscription_id:
        try:
            sub      = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
            plan     = PLAN_BY_PRICE.get(price_id, "pro")
            status   = sub.get("status", "active")
        except Exception as e:
            logger.error("Could not retrieve subscription %s: %s", subscription_id, e)
            status = "active"
    else:
        status = "active"

    if tenant_id:
        update_tenant_subscription(
            db, tenant_id, plan=plan,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_status=status,
        )
        logger.info("Checkout completed: tenant=%s plan=%s status=%s", tenant_id, plan, status)


def _on_subscription_change(db: Session, obj: dict):
    customer_id = obj.get("customer")
    sub_id      = obj.get("id")
    status      = obj.get("status", "active")
    items       = obj.get("items", {}).get("data", [])
    price_id    = items[0]["price"]["id"] if items else None
    plan        = PLAN_BY_PRICE.get(price_id, "pro")

    tenant = get_tenant_by_stripe_customer(db, customer_id)
    if tenant:
        update_tenant_subscription(
            db, tenant.id, plan=plan,
            stripe_subscription_id=sub_id,
            subscription_status=status,
        )
        logger.info("Subscription updated: tenant=%s plan=%s status=%s", tenant.id, plan, status)
