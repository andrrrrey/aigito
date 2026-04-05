"""
Kiosk API — called from the client screen (kiosk/tablet browser).
Provides company config and LiveKit token for WebRTC connection.
"""
import json
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Optional
from database import get_db
from companies.models import Company
from kiosk.models import DemoUsage
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
    avatar_greeting: Optional[str] = None
    chips: list[str]
    demo_mode_enabled: bool = False
    idle_timeout: int = 15
    video_quality: str = "auto"


class TokenResponse(BaseModel):
    token: str
    url: str
    room_name: str
    demo_remaining_seconds: Optional[float] = None


class DemoUsageReport(BaseModel):
    seconds_used: float


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
        avatar_greeting=company.avatar_greeting,
        chips=["Какие услуги вы предлагаете?", "Сколько стоит консультация?", "Запишите меня на приём"],
        demo_mode_enabled=company.demo_mode_enabled or False,
        idle_timeout=company.idle_timeout or 15,
        video_quality=company.video_quality or "auto",
    )


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


@router.post("/{company_slug}/token", response_model=TokenResponse)
async def get_livekit_token(company_slug: str, request: Request, language: str = "ru", db: AsyncSession = Depends(get_db)):
    company = await _get_company_by_slug(company_slug, db)

    # Demo mode: check IP usage limit
    demo_remaining_seconds = None
    if company.demo_mode_enabled:
        client_ip = _get_client_ip(request)
        result = await db.execute(
            select(DemoUsage).where(
                and_(DemoUsage.company_id == company.id, DemoUsage.ip_address == client_ip)
            )
        )
        usage = result.scalar_one_or_none()
        seconds_used = usage.seconds_used if usage else 0.0
        if seconds_used >= 60:
            raise HTTPException(status_code=403, detail="demo_limit_reached")
        demo_remaining_seconds = 60.0 - seconds_used

    room_name = f"kiosk-{company_slug}-{int(time.time())}"
    # Pass full company metadata to the agent
    # avatar_image_url must be a full public URL for LemonSlice API
    # Validate language to supported set
    supported_languages = {"ru", "en", "de", "zh"}
    lang = language if language in supported_languages else "ru"

    room_metadata = json.dumps({
        "company_id": str(company.id),
        "company_name": company.name,
        "location_description": company.location_description or "",
        "custom_rules": company.custom_rules or "",
        "voice_id": company.avatar_voice_id,
        "avatar_image_url": _make_public_url(company.avatar_image_url, request),
        "video_quality": company.video_quality or "auto",
        "language": lang,
        "avatar_greeting": company.avatar_greeting or "",
        "tts_provider": company.tts_provider or "openai",
        "openai_api_key": company.openai_api_key or "",
        "deepgram_api_key": company.deepgram_api_key or "",
        "elevenlabs_api_key": company.elevenlabs_api_key or "",
        "lemonslice_api_key": company.lemonslice_api_key or "",
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
        return TokenResponse(token=token, url=public_url, room_name=room_name, demo_remaining_seconds=demo_remaining_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LiveKit token generation failed: {e}")


@router.post("/{company_slug}/demo-usage")
async def report_demo_usage(
    company_slug: str,
    body: DemoUsageReport,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_by_slug(company_slug, db)
    if not company.demo_mode_enabled:
        return {"status": "ok"}

    client_ip = _get_client_ip(request)
    result = await db.execute(
        select(DemoUsage).where(
            and_(DemoUsage.company_id == company.id, DemoUsage.ip_address == client_ip)
        )
    )
    usage = result.scalar_one_or_none()
    if usage:
        usage.seconds_used = min(usage.seconds_used + body.seconds_used, 60.0)
    else:
        usage = DemoUsage(
            company_id=company.id,
            ip_address=client_ip,
            seconds_used=min(body.seconds_used, 60.0),
        )
        db.add(usage)
    return {"status": "ok", "total_seconds_used": usage.seconds_used}
