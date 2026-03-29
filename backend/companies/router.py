from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth.router import get_current_user
from auth.models import User
from companies.models import Company
from companies.schemas import CompanyCreate, CompanyUpdate, AvatarUpdate, CompanyResponse

router = APIRouter()


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.owner_id == current_user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found. Please create one first.")
    return company


@router.post("/", response_model=CompanyResponse, status_code=201)
async def create_company(
    body: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Company).where(Company.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already taken")
    company = Company(**body.model_dump(), owner_id=current_user.id)
    db.add(company)
    await db.flush()
    return company


@router.put("/me", response_model=CompanyResponse)
async def update_company(
    body: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.owner_id == current_user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    return company


@router.put("/me/avatar", response_model=CompanyResponse)
async def update_avatar(
    body: AvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.owner_id == current_user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    return company
