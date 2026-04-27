from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import AdminUser

router = APIRouter(prefix="/api/admin/auth", tags=["admin"])


class LoginIn(BaseModel):
    email: str = Field(max_length=512)
    password: str = Field(max_length=256)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminMeOut(BaseModel):
    id: int
    email: str


@router.post("/login", response_model=TokenOut)
def admin_login(data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    email = data.email.strip().lower()
    if len(email) < 3 or len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    user = db.execute(select(AdminUser).where(AdminUser.email == email)).scalars().first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    settings = get_settings()
    exp = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": str(user.id), "type": "admin"},
        expires_delta=exp,
    )
    return TokenOut(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=AdminMeOut)
def admin_me(admin: AdminUser = Depends(get_current_admin)) -> AdminMeOut:
    return AdminMeOut(id=admin.id, email=admin.email)
