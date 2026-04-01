"""
Kiosk API — called from the client screen (kiosk/tablet browser).
Provides company config and LiveKit token for WebRTC connection.
"""
import json
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from database import get_db
from companies.models import Company
from config import settings

router = APIRouter()


def _make_public_url(path: Optional[str], request: Request) -> Optional[str]:
    """Convert a local path like /uploads/avatars/... to a full public URL."""
    if not path:
        return path
    if path.startswith(("http://", "https://")):
        return path
    base = settings.public_base_url
    if not base:
        base = str(request.base_url).rstrip("/")
    return f"{base}{path}"


class KioskConfig(BaseModel):
    company_name: str
    avatar_image_url: Optional[str]
    avatar_voice_id: Optional[str]
    location_description: Optional[str]
    chips: list[str]


class TokenResponse(BaseModel):
    token: str
    url: str
    room_name: str


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
        chips=["Какие услуги вы предлагаете?", "Сколько стоит консультация?", "Запишите меня на приём"],
    )


@router.post("/{company_slug}/token", response_model=TokenResponse)
async def get_livekit_token(company_slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    company = await _get_company_by_slug(company_slug, db)

    room_name = f"kiosk-{company_slug}-{int(time.time())}"
    # Pass full company metadata to the agent
    # avatar_image_url must be a full public URL for LemonSlice API
    room_metadata = json.dumps({
        "company_id": str(company.id),
        "company_name": company.name,
        "location_description": company.location_description or "",
        "custom_rules": company.custom_rules or "",
        "voice_id": company.avatar_voice_id,
        "avatar_image_url": _make_public_url(company.avatar_image_url, request),
    })

    try:
        from livekit import api as lk_api

        # Create room with metadata so the agent can read it from ctx.room.metadata
        lkapi = lk_api.LiveKitAPI(
            url=settings.livekit_url.replace("ws://", "http://").replace("wss://", "https://"),
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        await lkapi.room.create_room(lk_api.CreateRoomRequest(
            name=room_name,
            metadata=room_metadata,
        ))
        await lkapi.aclose()

        token = (
            lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(f"kiosk-user-{int(time.time())}")
            .with_name("Kiosk User")
            .with_grants(lk_api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
        public_url = settings.livekit_public_url or settings.livekit_url
        return TokenResponse(token=token, url=public_url, room_name=room_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LiveKit token generation failed: {e}")
