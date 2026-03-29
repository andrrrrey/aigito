from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from auth.router import get_current_user
from auth.models import User
from companies.models import Company
from knowledge.models import KnowledgeDocument
from knowledge.ingest import extract_text, ingest_document

router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "csv"}


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    chunks_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


async def _get_company(user: User, db: AsyncSession) -> Company:
    result = await db.execute(select(Company).where(Company.owner_id == user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = await _get_company(current_user, db)
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.company_id == company.id)
    )
    return result.scalars().all()


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported. Use: {ALLOWED_EXTENSIONS}")

    company = await _get_company(current_user, db)
    content = await file.read()
    text = extract_text(file.filename, content)

    doc = KnowledgeDocument(
        company_id=company.id,
        filename=file.filename,
        file_type=ext,
        content_text=text,
    )
    db.add(doc)
    await db.flush()

    chunks = await ingest_document(str(company.id), str(doc.id), text)
    doc.chunks_count = chunks
    return doc


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.company_id == company.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)


@router.post("/rebuild", status_code=202)
async def rebuild_index(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Re-embed all documents and rebuild Qdrant index. Full impl in Stage 3."""
    company = await _get_company(current_user, db)
    return {"status": "scheduled", "company_id": str(company.id)}
