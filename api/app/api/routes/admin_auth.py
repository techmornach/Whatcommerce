"""Public admin login (JWT for /v1/admin/*)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_admin_access_token, verify_password
from app.db.session import get_db
from app.models.admin_user import AdminUser

router = APIRouter(prefix="/v1/auth/admin", tags=["admin-auth"])


class AdminLoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
async def admin_login(body: AdminLoginBody, db: AsyncSession = Depends(get_db)) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_admin_access_token(admin_id=user.id, email=user.email, role=user.role)
    return {"access_token": token, "token_type": "bearer"}
