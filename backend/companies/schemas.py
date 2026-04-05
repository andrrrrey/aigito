from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, model_validator


def _mask_key(key: Optional[str]) -> Optional[str]:
    """Return masked version of API key: show only last 4 chars."""
    if not key:
        return None
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


class CompanyBase(BaseModel):
    name: str
    slug: str
    location_description: Optional[str] = None
    custom_rules: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    blocked_topics: Optional[List[str]] = None
    enable_web_search: bool = False


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    location_description: Optional[str] = None
    custom_rules: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    blocked_topics: Optional[List[str]] = None
    enable_web_search: Optional[bool] = None
    demo_mode_enabled: Optional[bool] = None
    idle_timeout: Optional[int] = None
    video_quality: Optional[Literal["auto", "max"]] = None
    avatar_greeting: Optional[str] = None
    tts_provider: Optional[Literal["openai", "elevenlabs"]] = None


class AvatarUpdate(BaseModel):
    avatar_image_url: Optional[str] = None
    avatar_voice_id: Optional[str] = None
    avatar_prompt: Optional[str] = None
    avatar_greeting: Optional[str] = None


class ApiKeysUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    lemonslice_api_key: Optional[str] = None


class ApiKeysResponse(BaseModel):
    openai_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    lemonslice_api_key: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def mask_keys(cls, data):
        if hasattr(data, "__dict__"):
            # ORM object
            return {
                "openai_api_key": _mask_key(getattr(data, "openai_api_key", None)),
                "deepgram_api_key": _mask_key(getattr(data, "deepgram_api_key", None)),
                "elevenlabs_api_key": _mask_key(getattr(data, "elevenlabs_api_key", None)),
                "lemonslice_api_key": _mask_key(getattr(data, "lemonslice_api_key", None)),
            }
        # dict
        return {
            "openai_api_key": _mask_key(data.get("openai_api_key")),
            "deepgram_api_key": _mask_key(data.get("deepgram_api_key")),
            "elevenlabs_api_key": _mask_key(data.get("elevenlabs_api_key")),
            "lemonslice_api_key": _mask_key(data.get("lemonslice_api_key")),
        }


class CompanyResponse(CompanyBase):
    id: UUID
    avatar_image_url: Optional[str] = None
    avatar_voice_id: Optional[str] = None
    avatar_prompt: Optional[str] = None
    avatar_greeting: Optional[str] = None
    demo_mode_enabled: bool = False
    idle_timeout: int = 15
    video_quality: str = "auto"
    tts_provider: str = "openai"
    plan: str
    minutes_limit: int
    minutes_used: float
    created_at: datetime

    class Config:
        from_attributes = True
