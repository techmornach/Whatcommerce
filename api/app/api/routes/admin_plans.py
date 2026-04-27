from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, BillingPlan

router = APIRouter(prefix="/api/admin/billing-plans", tags=["admin"])


class BillingPlanOut(BaseModel):
    id: int
    key: str
    name: str
    max_products: int
    price_monthly_ngn: int
    price_yearly_ngn: int
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class BillingPlanUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    max_products: int | None = Field(default=None, ge=0, le=1_000_000)
    price_monthly_ngn: int | None = Field(default=None, ge=0)
    price_yearly_ngn: int | None = Field(default=None, ge=0)
    display_order: int | None = None
    is_active: bool | None = None


@router.get("", response_model=list[BillingPlanOut])
def list_plans(
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[BillingPlan]:
    return list(
        db.execute(select(BillingPlan).order_by(BillingPlan.display_order, BillingPlan.id))
        .scalars()
        .all()
    )


@router.put("/{plan_id}", response_model=BillingPlanOut)
def update_plan(
    plan_id: int,
    body: BillingPlanUpdateIn,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BillingPlan:
    plan = db.get(BillingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(plan, k, v)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
