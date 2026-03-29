"""
Kiosk API — called from the client screen (kiosk/tablet browser).
Provides company config and LiveKit token for WebRTC connection.
"""
import json
import time
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from pydantic import BaseModel
from database import get_db
from companies.models import Company
from config import settings

router = APIRouter()


class KioskConfig(BaseModel):
    company_name: str
    avatar_image_url: str | None
    avatar_voice_id: str | None
    location_description: str | None
    chips: list[str]  # Quick-reply suggestions


class TokenResponse(BaseModel):
    token: str
    url: str


async def _get_company_by_slug(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{slug}' not found")
    return company


@router.get("/{company_slug}/config", response_model=KioskConfig)
async def get_kiosk_config(company_slug: str, db: AsyncSession = Depends(get_db)):
    company = await _get_company_by_slug(company_slug, db)
    return KioskConfig(
        company_name=company.name,
        avatar_image_url=company.avatar_image_url,
        avatar_voice_id=company.avatar_voice_id,
        location_description=company.location_description,
        chips=["Какие услуги?", "Сколько стоит?", "Записаться"],
    )


@router.post("/{company_slug}/token", response_model=TokenResponse)
async def get_livekit_token(company_slug: str, db: AsyncSession = Depends(get_db)):
    company = await _get_company_by_slug(company_slug, db)

    try:
        from livekit.api import AccessToken, VideoGrants
        room_name = f"kiosk-{company_slug}-{int(time.time())}"
        room_metadata = json.dumps({
            "company_id": str(company.id),
            "avatar_image_url": company.avatar_image_url,
            "voice_id": company.avatar_voice_id,
        })
        token = (
            AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(f"kiosk-user-{int(time.time())}")
            .with_name("Kiosk User")
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .with_metadata(room_metadata)
            .to_jwt()
        )
        return TokenResponse(token=token, url=settings.livekit_url)
    except ImportError:
        # livekit not available in stage 1 — return stub
        return TokenResponse(
            token="stub-token-livekit-not-installed",
            url=settings.livekit_url,
        )
