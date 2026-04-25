import hashlib
import hmac
import secrets
from typing import Any

import httpx

from app.core.config import get_settings

PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"


def build_payment_reference(tenant_id: str) -> str:
    suffix = secrets.token_hex(4)
    return f"wc_tnt_{tenant_id}_{suffix}"[:100]


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    secret = get_settings().paystack_secret_key
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


async def initialize_transaction(
    *,
    email: str,
    amount_kobo: int,
    reference: str,
    metadata: dict[str, Any],
    currency: str = "NGN",
) -> dict[str, Any]:
    secret = get_settings().paystack_secret_key
    if not secret:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")

    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "metadata": metadata,
        "currency": currency,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PAYSTACK_INITIALIZE_URL,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        data = response.json()
        if not response.is_success:
            msg = data.get("message", response.text)
            raise RuntimeError(f"Paystack initialize failed ({response.status_code}): {msg}")
        if not data.get("status"):
            raise RuntimeError(f"Paystack initialize rejected: {data.get('message', data)}")
        return data
