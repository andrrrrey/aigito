from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
import os
from database import get_db, AsyncSessionLocal
from auth.router import get_current_user
from auth.models import User
from companies.models import Company
from knowledge.models import KnowledgeDocument
from knowledge.ingest import extract_text, ingest_document, delete_document_chunks, rebuild_company_index
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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
        select(KnowledgeDocument)
        .where(KnowledgeDocument.company_id == company.id)
        .order_by(KnowledgeDocument.uploaded_at.desc())
    )
    return result.scalars().all()


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Supported: {ALLOWED_EXTENSIONS}")

    company = await _get_company(current_user, db)
    content = await file.read()
    text = extract_text(file.filename, content)

    doc = KnowledgeDocument(
        company_id=company.id,
        filename=file.filename,
        file_type=ext,
        content_text=text,
        chunks_count=0,
    )
    db.add(doc)
    await db.flush()
    # Commit the document row before scheduling the background task so the
    # fresh session opened inside the task can read it. Previously we passed
    # the request-scoped `db` into the task, but FastAPI closes that session
    # right after the response is sent, breaking the background DB update.
    await db.commit()
    await db.refresh(doc)

    doc_id = str(doc.id)
    company_id = str(company.id)
    background_tasks.add_task(_ingest_and_update, doc_id, company_id, text)

    return doc


async def _ingest_and_update(doc_id: str, company_id: str, text: str):
    """Background task: embed chunks and update chunks_count in a fresh DB session."""
    try:
        chunks = await ingest_document(company_id, doc_id, text)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.chunks_count = chunks
                await db.commit()
        logger.info("Ingest done: doc=%s chunks=%d", doc_id, chunks)
    except Exception:
        logger.exception("Background ingestion failed for doc=%s", doc_id)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    background_tasks: BackgroundTasks,
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

    company_id = str(company.id)
    background_tasks.add_task(delete_document_chunks, company_id, str(doc_id))
    await db.delete(doc)


@router.post("/rebuild", status_code=202)
async def rebuild_index(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-embed all documents and rebuild the Qdrant collection from scratch."""
    company = await _get_company(current_user, db)
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.company_id == company.id)
    )
    docs = result.scalars().all()
    docs_data = [
        {"id": str(d.id), "content_text": d.content_text or ""}
        for d in docs
    ]
    company_id = str(company.id)
    background_tasks.add_task(rebuild_company_index, company_id, docs_data)
    return {"status": "rebuilding", "company_id": company_id, "documents": len(docs_data)}


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)


@router.get("/memory-stats")
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the count of self-learned memory points for the company."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    company = await _get_company(current_user, db)
    company_id = str(company.id)
    collection_name = f"company_{company_id}"
    try:
        qdrant = _get_qdrant_client()
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            return {"learned_count": 0}
        result = qdrant.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value="learned"))]
            ),
            exact=True,
        )
        return {"learned_count": result.count}
    except Exception as e:
        logger.warning("memory-stats failed: %s", e)
        return {"learned_count": 0}


@router.delete("/memory", status_code=204)
async def clear_memory(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all self-learned memory points for the company."""
    company = await _get_company(current_user, db)
    company_id = str(company.id)
    background_tasks.add_task(_delete_learned_points, company_id)


async def _delete_learned_points(company_id: str):
    """Background task: delete all learned Qdrant points for the company."""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant = _get_qdrant_client()
        collection_name = f"company_{company_id}"
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            return
        qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value="learned"))]
            ),
        )
        logger.info("Cleared learned memory for company=%s", company_id)
    except Exception:
        logger.exception("Failed to clear learned memory for company=%s", company_id)
