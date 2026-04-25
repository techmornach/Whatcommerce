from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.subscription_payment import start_paystack_subscription_checkout

router = APIRouter(
    prefix="/v1/internal/payments",
    tags=["internal-payments"],
    dependencies=[Depends(require_internal_secret)],
)


class PaystackInitializeBody(BaseModel):
    tenant_id: UUID
    customer_email: Optional[EmailStr] = None


@router.post("/paystack/initialize")
async def paystack_initialize(
    body: PaystackInitializeBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    email = body.customer_email or tenant.owner_email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide customer_email or set tenant.owner_email first",
        )

    try:
        out = await start_paystack_subscription_checkout(db, tenant, str(email))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    await db.commit()

    return {
        "authorization_url": out.get("authorization_url"),
        "access_code": out.get("access_code"),
        "reference": out.get("reference"),
        "amount_kobo": out.get("amount_kobo"),
    }
