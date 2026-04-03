from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


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


class AvatarUpdate(BaseModel):
    avatar_image_url: Optional[str] = None
    avatar_voice_id: Optional[str] = None
    avatar_prompt: Optional[str] = None


class CompanyResponse(CompanyBase):
    id: UUID
    avatar_image_url: Optional[str] = None
    avatar_voice_id: Optional[str] = None
    avatar_prompt: Optional[str] = None
    demo_mode_enabled: bool = False
    idle_timeout: int = 15
    plan: str
    minutes_limit: int
    minutes_used: float
    created_at: datetime

    class Config:
        from_attributes = True
