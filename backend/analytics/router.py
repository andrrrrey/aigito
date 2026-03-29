from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
from uuid import UUID
from database import get_db
from auth.router import get_current_user
from auth.models import User
from companies.models import Company
from analytics.models import Dialog, DialogMessage

router = APIRouter()


async def _get_company(user: User, db: AsyncSession) -> Company:
    result = await db.execute(select(Company).where(Company.owner_id == user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


class SummaryResponse(BaseModel):
    dialogs_today: int
    dialogs_total: int
    minutes_used: float
    minutes_limit: int
    avg_duration_seconds: Optional[float]


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = await _get_company(current_user, db)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    dialogs_today = await db.scalar(
        select(func.count(Dialog.id)).where(
            and_(Dialog.company_id == company.id, Dialog.started_at >= today_start)
        )
    )
    dialogs_total = await db.scalar(
        select(func.count(Dialog.id)).where(Dialog.company_id == company.id)
    )
    avg_duration = await db.scalar(
        select(func.avg(Dialog.duration_seconds)).where(
            and_(Dialog.company_id == company.id, Dialog.duration_seconds.isnot(None))
        )
    )

    return SummaryResponse(
        dialogs_today=dialogs_today or 0,
        dialogs_total=dialogs_total or 0,
        minutes_used=company.minutes_used,
        minutes_limit=company.minutes_limit,
        avg_duration_seconds=avg_duration,
    )


class DialogResponse(BaseModel):
    id: UUID
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    language: str
    satisfaction_score: Optional[int]
    topics: Optional[List[str]]

    class Config:
        from_attributes = True


@router.get("/dialogs", response_model=List[DialogResponse])
async def list_dialogs(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    filters = [Dialog.company_id == company.id]
    if date_from:
        filters.append(Dialog.started_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(Dialog.started_at <= datetime.combine(date_to, datetime.max.time()))

    result = await db.execute(
        select(Dialog)
        .where(and_(*filters))
        .order_by(Dialog.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/dialogs/{dialog_id}/messages")
async def get_dialog_messages(
    dialog_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    # Verify dialog belongs to company
    dialog = await db.scalar(
        select(Dialog).where(
            and_(Dialog.id == dialog_id, Dialog.company_id == company.id)
        )
    )
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    result = await db.execute(
        select(DialogMessage)
        .where(DialogMessage.dialog_id == dialog_id)
        .order_by(DialogMessage.timestamp)
    )
    messages = result.scalars().all()
    return [
        {"role": m.role, "content": m.content, "timestamp": m.timestamp}
        for m in messages
    ]


@router.get("/topics")
async def get_top_topics(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = await _get_company(current_user, db)
    result = await db.execute(
        select(Dialog.topics).where(
            and_(Dialog.company_id == company.id, Dialog.topics.isnot(None))
        ).limit(500)
    )
    from collections import Counter
    all_topics: List[str] = []
    for row in result.scalars():
        if isinstance(row, list):
            all_topics.extend(row)
    counts = Counter(all_topics).most_common(10)
    return [{"topic": t, "count": c} for t, c in counts]


@router.get("/usage")
async def get_usage(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = await _get_company(current_user, db)
    return {
        "minutes_used": round(company.minutes_used, 2),
        "minutes_limit": company.minutes_limit,
        "minutes_remaining": max(0, round(company.minutes_limit - company.minutes_used, 2)),
        "plan": company.plan,
    }


@router.get("/dialogs-chart")
async def get_dialogs_chart(
    days: int = Query(30, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns daily dialog counts for the last N days (for Chart.js)."""
    from datetime import timedelta
    company = await _get_company(current_user, db)
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", Dialog.started_at).label("day"),
            func.count(Dialog.id).label("count"),
        )
        .where(and_(Dialog.company_id == company.id, Dialog.started_at >= start_date))
        .group_by(func.date_trunc("day", Dialog.started_at))
        .order_by(func.date_trunc("day", Dialog.started_at))
    )
    rows = result.all()
    return [{"date": r.day.strftime("%Y-%m-%d"), "count": r.count} for r in rows]
