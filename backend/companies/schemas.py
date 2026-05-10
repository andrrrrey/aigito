import re
from typing import Optional, List, Literal, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, field_validator, model_validator


def _mask_key(key: Optional[str]) -> Optional[str]:
    """Return masked version of API key: show only last 4 chars."""
    if not key:
        return None
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


def _validate_slug(v: str) -> str:
    v = v.strip().lower()
    if len(v) < 2:
        raise ValueError("Slug must be at least 2 characters")
    if len(v) > 64:
        raise ValueError("Slug must be at most 64 characters")
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
        raise ValueError("Slug may only contain lowercase latin letters, digits, and hyphens (not at start/end)")
    return v


class CompanyBase(BaseModel):
    name: str
    slug: str
    location_description: Optional[str] = None
    custom_rules: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    blocked_topics: Optional[List[str]] = None
    enable_web_search: bool = False


class CompanyCreate(CompanyBase):
    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return _validate_slug(v)


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    location_description: Optional[str] = None
    custom_rules: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    blocked_topics: Optional[List[str]] = None
    enable_web_search: Optional[bool] = None
    demo_mode_enabled: Optional[bool] = None
    idle_timeout: Optional[int] = None
    video_quality: Optional[Literal["auto", "max"]] = None
    enable_video_generation: Optional[bool] = None
    avatar_greeting: Optional[str] = None
    tts_provider: Optional[Literal["openai", "elevenlabs"]] = None
    avatar_memory_enabled: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_slug(v)


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


class PersonalityUpdate(BaseModel):
    # Group 1: Voice & Pacing
    speech_pace: Optional[float] = None
    pause_frequency: Optional[float] = None
    pause_duration: Optional[float] = None
    pitch_variation: Optional[float] = None
    volume_variation: Optional[float] = None
    breath_sounds_enabled: Optional[bool] = None
    breath_sounds: Optional[float] = None
    speech_imperfections: Optional[float] = None
    # Group 2: Emotional Expression
    emotional_range: Optional[float] = None
    baseline_mood: Optional[Literal["melancholic", "neutral", "warm", "playful", "energetic", "professional"]] = None
    enthusiasm_level: Optional[float] = None
    empathy_level: Optional[float] = None
    tenderness: Optional[float] = None
    vulnerability: Optional[float] = None
    # Group 3: Humor
    humor_level: Optional[float] = None
    humor_style: Optional[Literal["dry", "warm", "self_ironic", "observational", "playful", "none"]] = None
    laughter_frequency: Optional[float] = None
    teasing: Optional[float] = None
    # Group 4: Language Style
    formality: Optional[float] = None
    slang_usage: Optional[float] = None
    vocabulary_richness: Optional[float] = None
    sentence_length: Optional[float] = None
    filler_words: Optional[float] = None
    interjections: Optional[float] = None
    # Group 5: Conversation Behavior
    initiative_level: Optional[float] = None
    question_frequency: Optional[float] = None
    memory_within_session: Optional[float] = None
    interruption_allowed: Optional[bool] = None
    response_latency: Optional[float] = None
    disagreement_comfort: Optional[float] = None
    silence_tolerance: Optional[float] = None
    # Idle dialogue — proactive speech after N seconds of user silence
    idle_dialogue_enabled: Optional[bool] = None
    idle_dialogue_timeout: Optional[int] = None   # seconds, default 30
    # Group 6: Identity
    character_name: Optional[str] = None
    character_age: Optional[int] = None
    character_gender: Optional[Literal["female", "male", "nonbinary"]] = None
    backstory: Optional[str] = None
    core_values: Optional[List[str]] = None
    obsessions: Optional[List[str]] = None
    taboos: Optional[str] = None
    self_awareness_level: Optional[Literal["denies", "neutral", "philosophical", "playful"]] = None
    # Group 7: Business Logic
    primary_purpose: Optional[Literal["companion", "consultant", "salesperson", "receptionist", "entertainer", "support"]] = None
    product_promotion: Optional[float] = None
    escalation_behavior: Optional[Literal["admit_honestly", "redirect_to_human", "request_contact", "improvise"]] = None
    forbidden_topics: Optional[List[str]] = None
    required_disclosures: Optional[str] = None
    # Group 8: Nonverbal Behavior
    smile_frequency: Optional[float] = None
    gesture_intensity: Optional[float] = None
    eye_contact: Optional[float] = None
    gaze_movement: Optional[float] = None
    blink_naturalness: Optional[float] = None
    micro_movements: Optional[float] = None
    facial_asymmetry: Optional[float] = None
    emotion_delay: Optional[float] = None
    # Group 9: Preset
    preset: Optional[str] = None


class VerifyElevenlabsRequest(BaseModel):
    elevenlabs_api_key: Optional[str] = None


class VerifyElevenlabsResponse(BaseModel):
    valid: bool
    detail: str


class CompanyResponse(CompanyBase):
    id: UUID
    avatar_image_url: Optional[str] = None
    avatar_voice_id: Optional[str] = None
    avatar_prompt: Optional[str] = None
    avatar_greeting: Optional[str] = None
    demo_mode_enabled: bool = False
    idle_timeout: int = 15
    video_quality: str = "auto"
    enable_video_generation: bool = True
    tts_provider: str = "openai"
    avatar_memory_enabled: bool = True
    personality_settings: Optional[Dict[str, Any]] = None
    plan: str
    minutes_limit: int
    minutes_used: float
    created_at: datetime

    class Config:
        from_attributes = True
