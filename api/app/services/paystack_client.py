import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def initialize_transaction(
    *,
    email: str,
    amount_ngn: int,
    reference: str,
    metadata: dict[str, Any],
) -> tuple[str, str]:
    """
    Create a Paystack payment URL. Returns (authorization_url, reference).
    With no secret key (dev), returns a placeholder URL and the same reference.
    """
    settings = get_settings()
    secret = settings.paystack_secret_key
    amount_kobo = max(1, int(amount_ngn)) * 100

    if not secret:
        url = f"https://paystack.com/pay/__dev_placeholder__?ref={reference}"
        logger.warning(
            "PAYSTACK_SECRET_KEY not set; using placeholder payment URL (dev only)"
        )
        return url, reference

    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "metadata": metadata,
        "currency": "NGN",
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "https://api.paystack.co/transaction/initialize",
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
        )
    r.raise_for_status()
    body = r.json()
    if not body.get("status"):
        raise RuntimeError(body.get("message", "Paystack error"))
    data = body.get("data") or {}
    auth_url = str(data.get("authorization_url") or "")
    ref = str(data.get("reference") or reference)
    if not auth_url:
        raise RuntimeError("Paystack response missing authorization_url")
    return auth_url, ref
