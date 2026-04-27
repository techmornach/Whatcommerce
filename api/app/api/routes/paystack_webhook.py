import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.paystack_webhook_service import process_paystack_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paystack", tags=["paystack"])


def _verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not raw_body or not secret:
        return False
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def _hmac_secret() -> str | None:
    s = get_settings()
    if s.paystack_webhook_secret:
        return s.paystack_webhook_secret.strip()
    if s.paystack_secret_key:
        return s.paystack_secret_key.strip()
    return None


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    raw = await request.body()
    sig = request.headers.get("X-Paystack-Signature", "")
    secret = _hmac_secret()

    if not secret:
        if get_settings().api_env == "dev":
            logger.warning("No Paystack secret; webhook not verified (set PAYSTACK_SECRET_KEY)")
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Paystack not configured",
            )
        return {"status": "rejected", "reason": "no_secret"}

    if not _verify_signature(raw, sig, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    try:
        payload: dict[str, Any] = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON"
        ) from e

    out = process_paystack_payload(db, payload)
    return {**{k: str(v) for k, v in out.items()}, "status": "ok"}
