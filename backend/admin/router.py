from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import hash_password
from auth.models import User
from auth.router import get_current_superuser
from companies.models import Company
from analytics.models import Dialog
from database import get_db

router = APIRouter()


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: Optional[datetime]
    companies_count: int
    dialogs_count: int


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    is_superuser: bool = False


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    users_result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = users_result.scalars().all()

    companies_result = await db.execute(
        select(Company.owner_id, func.count(Company.id).label("cnt")).group_by(Company.owner_id)
    )
    companies_by_owner = {row.owner_id: row.cnt for row in companies_result}

    dialogs_result = await db.execute(
        select(Company.owner_id, func.count(Dialog.id).label("cnt"))
        .join(Dialog, Dialog.company_id == Company.id)
        .group_by(Company.owner_id)
    )
    dialogs_by_owner = {row.owner_id: row.cnt for row in dialogs_result}

    return [
        UserListItem(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            created_at=u.created_at,
            companies_count=companies_by_owner.get(u.id, 0),
            dialogs_count=dialogs_by_owner.get(u.id, 0),
        )
        for u in users
    ]


@router.post("/users", response_model=UserListItem, status_code=201)
async def create_user(
    body: UserCreateRequest,
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_superuser=body.is_superuser,
    )
    db.add(user)
    await db.flush()
    return UserListItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        companies_count=0,
        dialogs_count=0,
    )


@router.patch("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    current_admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None:
        conflict = await db.execute(select(User).where(User.email == body.email, User.id != user_id))
        if conflict.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already taken")
        user.email = body.email
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_superuser is not None:
        user.is_superuser = body.is_superuser

    companies_result = await db.execute(
        select(func.count(Company.id)).where(Company.owner_id == user.id)
    )
    companies_count = companies_result.scalar() or 0

    dialogs_result = await db.execute(
        select(func.count(Dialog.id))
        .join(Company, Dialog.company_id == Company.id)
        .where(Company.owner_id == user.id)
    )
    dialogs_count = dialogs_result.scalar() or 0

    return UserListItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        companies_count=companies_count,
        dialogs_count=dialogs_count,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    if str(user_id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
