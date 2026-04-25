"""Whatcommerce bot: deterministic onboarding → tenant + Paystack link."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import plan_choice_prompt, subscription_amount_ngn
from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.core.config import get_settings
from app.models.onboarding_session import OnboardingSession
from app.models.platform import PlatformSettings
from app.models.tenant import PlanTier, Tenant, TenantStatus
from app.services.store_link_urls import wa_link_public_url
from app.services.subscription_payment import start_paystack_subscription_checkout
from app.services.whatcommerce_agent import run_whatcommerce_agent

logger = logging.getLogger(__name__)


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

_AWAIT_START = "await_start"
_COLLECT_NAME = "collect_name"
_COLLECT_BUSINESS = "collect_business"
_COLLECT_ADDRESS = "collect_address"
_COLLECT_EMAIL = "collect_email"
_CHOOSE_PLAN = "choose_plan"
_CHOOSE_PERIOD = "choose_period"
_PAYMENT_SENT = "payment_sent"

_AFFIRM = frozenset(
    {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "start", "go", "lets go", "let's go", "subscribe", "ready"}
)


def _digits_phone(raw: str) -> str:
    return "".join(c for c in raw if c.isdigit())


def _affirmative(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    if t in _AFFIRM:
        return True
    if "get started" in t or t.startswith("yes"):
        return True
    return False


def _parse_plan(text: str) -> str | None:
    t = text.strip().lower()
    if t in {"1", "lite", "l"}:
        return PlanTier.lite.value
    if t in {"2", "standard", "s"}:
        return PlanTier.standard.value
    if t in {"3", "premium", "p"}:
        return PlanTier.premium.value
    for tier in ("lite", "standard", "premium"):
        if tier in t:
            return tier
    return None


def _parse_period(text: str) -> str | None:
    t = text.strip().lower()
    if t in {"monthly", "month", "m", "1"}:
        return "monthly"
    if t in {"yearly", "year", "annual", "y", "2"}:
        return "yearly"
    return None


def _valid_email(text: str) -> bool:
    try:
        TypeAdapter(EmailStr).validate_python(text.strip())
        return True
    except (ValueError, ValidationError):
        return False


def _data(sess: OnboardingSession) -> dict[str, Any]:
    raw = sess.data
    if not isinstance(raw, dict):
        return {}
    return raw


def _set_data(sess: OnboardingSession, **kwargs: Any) -> None:
    d = dict(_data(sess))
    d.update(kwargs)
    sess.data = d


async def handle_whatcommerce_inbound(db: AsyncSession, from_e164: str, raw_text: str) -> list[str]:
    phone = _digits_phone(from_e164)
    if len(phone) < 10:
        return ["We could not read a valid phone number from this chat."]

    text = (raw_text or "").strip()
    lower = text.lower()

    result = await db.execute(select(Tenant).where(Tenant.onboarding_phone_e164 == phone))
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant and existing_tenant.status == TenantStatus.active.value:
        lines = [
            "Your Whatcommerce workspace is already active.",
            "If you need help, reply SUPPORT (coming soon) or email your administrator.",
        ]
        now = datetime.now(timezone.utc)
        url = wa_link_public_url(existing_tenant)
        ex = existing_tenant.wa_link_expires_at
        if (
            url
            and ex
            and _utc(ex) > now
            and not existing_tenant.store_manager_phone_e164
        ):
            lines.append(f"To link your *business* WhatsApp, open this page (QR + steps): {url}")
        await db.commit()
        return lines

    if existing_tenant and existing_tenant.status == TenantStatus.inactive.value:
        if "new link" in lower or "payment link" in lower or "pay again" in lower:
            email = existing_tenant.owner_email
            if not email:
                await db.commit()
                return [
                    "We need an email on file to generate a Paystack link. "
                    "Please contact support to add one, or complete onboarding again with RESET."
                ]
            try:
                checkout = await start_paystack_subscription_checkout(db, existing_tenant, str(email))
            except RuntimeError as exc:
                await db.rollback()
                return [f"Could not start checkout: {exc}"]
            url = checkout.get("authorization_url") or ""
            if not url:
                await db.rollback()
                return ["Paystack did not return a link. Please try again shortly."]
            await db.execute(delete(OnboardingSession).where(OnboardingSession.phone_e164 == phone))
            await db.commit()
            return [
                "Here is a fresh Paystack payment link:",
                url,
                "After you pay, activation happens automatically within a minute.",
            ]
        await db.commit()
        return [
            "Your account is created but still *inactive* until Paystack confirms payment.",
            "Say NEW LINK if you need another payment URL.",
        ]

    if lower == "reset":
        await db.execute(delete(OnboardingSession).where(OnboardingSession.phone_e164 == phone))
        await db.commit()
        return ["Signup progress cleared for this number. Send hi to start again."]

    sess_result = await db.execute(select(OnboardingSession).where(OnboardingSession.phone_e164 == phone))
    sess = sess_result.scalar_one_or_none()

    if sess is None and text.strip() and not _affirmative(text):
        settings = get_settings()
        if settings.openai_api_key:
            prow = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
            faq = (prow.knowledge_base_text if prow else "") or ""
            try:
                chunks = await run_whatcommerce_agent(user_message=text, knowledge_base_text=faq)
                await db.commit()
                return chunks
            except Exception:
                logger.exception("whatcommerce_agent_failed")
                await db.rollback()

    if sess is None:
        sess = OnboardingSession(phone_e164=phone, state=_AWAIT_START, data={})
        db.add(sess)
        await db.flush()

    if sess.state == _AWAIT_START:
        if not text:
            await db.commit()
            return [
                "Welcome to Whatcommerce — run your shop from WhatsApp.",
                "There is no free plan. When you're ready, reply YES and we'll collect a few details, "
                "then send you a secure Paystack link.",
            ]
        if _affirmative(text):
            sess.state = _COLLECT_NAME
            await db.commit()
            return ["Great. What is your full name?"]
        await db.commit()
        return ["Reply YES when you'd like to subscribe and set up your business."]

    if sess.state == _COLLECT_NAME:
        if len(text) < 2:
            await db.commit()
            return ["Please send your name (at least 2 characters)."]
        _set_data(sess, owner_name=text.strip())
        sess.state = _COLLECT_BUSINESS
        await db.commit()
        return ["Thanks. What is your *business name*?"]

    if sess.state == _COLLECT_BUSINESS:
        if len(text) < 2:
            await db.commit()
            return ["Please send your business name."]
        _set_data(sess, business_name=text.strip())
        sess.state = _COLLECT_ADDRESS
        await db.commit()
        return ["Got it. What is your *business address* (where you ship from or operate)?"]

    if sess.state == _COLLECT_ADDRESS:
        if len(text) < 5:
            await db.commit()
            return ["Please send a fuller business address."]
        _set_data(sess, business_address=text.strip())
        sess.state = _COLLECT_EMAIL
        await db.commit()
        return [
            "Paystack needs a customer email for receipts.",
            "Send a valid email address (example: you@domain.com).",
        ]

    if sess.state == _COLLECT_EMAIL:
        if not _valid_email(text):
            await db.commit()
            return ["That doesn't look like a valid email. Please try again."]
        _set_data(sess, owner_email=text.strip())
        sess.state = _CHOOSE_PLAN
        await db.commit()
        return [await plan_choice_prompt(db)]

    if sess.state == _CHOOSE_PLAN:
        tier = _parse_plan(text)
        if not tier:
            await db.commit()
            return ["Please reply 1 (Lite), 2 (Standard), or 3 (Premium).", await plan_choice_prompt(db)]
        _set_data(sess, plan_tier=tier)
        sess.state = _CHOOSE_PERIOD
        await db.commit()
        return [
            f"You picked *{tier.title()}*. Now choose billing:",
            "Reply MONTHLY or YEARLY (yearly = 12× the monthly price for MVP).",
        ]

    if sess.state == _CHOOSE_PERIOD:
        period = _parse_period(text)
        if not period:
            await db.commit()
            return ["Please reply MONTHLY or YEARLY."]
        d = _data(sess)
        tier = str(d.get("plan_tier") or PlanTier.lite.value)
        amount = await subscription_amount_ngn(db, tier, period)
        tenant = Tenant(
            owner_name=str(d.get("owner_name") or "Unknown"),
            business_name=str(d.get("business_name") or "Business"),
            business_address=str(d.get("business_address") or ""),
            plan_tier=tier,
            billing_period=period,
            status=TenantStatus.inactive.value,
            onboarding_phone_e164=phone,
            owner_email=str(d.get("owner_email") or ""),
        )
        db.add(tenant)
        await db.flush()

        email = str(d.get("owner_email") or "")
        try:
            checkout = await start_paystack_subscription_checkout(db, tenant, email)
        except RuntimeError as exc:
            await db.delete(tenant)
            await db.commit()
            return [
                "We could not start Paystack checkout (check PAYSTACK_SECRET_KEY on the server).",
                f"Detail: {exc}",
                "Reply MONTHLY or YEARLY again to retry once it's fixed.",
            ]

        url = checkout.get("authorization_url") or ""
        if not url:
            await db.delete(tenant)
            await db.commit()
            return ["Paystack returned no payment URL. Please try again later."]

        sess.state = _PAYMENT_SENT
        sess.tenant_id = tenant.id
        _set_data(sess, billing_period=period, plan_tier=tier)
        await db.commit()
        return [
            f"You're on *{tier.title()}* — *{period}* — total due now: ₦{amount:,}.",
            "Pay here (secure Paystack link):",
            url,
            "After payment, your account flips to active automatically — no need to text \"paid\".",
        ]

    if sess.state == _PAYMENT_SENT:
        if sess.tenant_id:
            tenant = await db.get(Tenant, sess.tenant_id)
            if tenant and tenant.status == TenantStatus.active.value:
                await db.refresh(tenant)
                url = wa_link_public_url(tenant)
                lines = ["Payment confirmed — your account is now *active*."]
                if url:
                    lines.append(f"Next: link your business WhatsApp. Open this page (steps + helper QR): {url}")
                else:
                    lines.append(
                        "Next: run the store-manager worker with your TENANT_ID and scan the terminal QR."
                    )
                await db.execute(delete(OnboardingSession).where(OnboardingSession.phone_e164 == phone))
                await db.commit()
                return lines
        await db.commit()
        return [
            "Waiting for Paystack to confirm your payment.",
            "If something went wrong, say NEW LINK (once your server email is set on the tenant).",
        ]

    await db.commit()
    return ["Something went wrong in onboarding. Send RESET to start over."]
