import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth.router import get_current_user
from auth.models import User
from companies.models import Company
from companies.schemas import CompanyCreate, CompanyUpdate, AvatarUpdate, CompanyResponse

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads" / "avatars"


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


@router.post("/me/avatar/upload", response_model=CompanyResponse)
async def upload_avatar_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Тип файла '{file.content_type}' не поддерживается. Допустимы: JPEG, PNG, WebP, GIF",
        )

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимум 5 МБ")

    result = await db.execute(select(Company).where(Company.owner_id == current_user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Delete old uploaded avatar if it exists
    if company.avatar_image_url and company.avatar_image_url.startswith("/uploads/avatars/"):
        old_path = UPLOADS_DIR / company.avatar_image_url.split("/")[-1]
        old_path.unlink(missing_ok=True)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{company.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = UPLOADS_DIR / filename
    filepath.write_bytes(content)

    company.avatar_image_url = f"/uploads/avatars/{filename}"
    return company
