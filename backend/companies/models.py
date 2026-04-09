import uuid
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)  # used in kiosk URL

    # Avatar settings
    avatar_image_url = Column(String)
    avatar_voice_id = Column(String)
    avatar_prompt = Column(Text)
    avatar_greeting = Column(Text)
    location_description = Column(String)

    # Rules
    custom_rules = Column(Text)
    allowed_topics = Column(JSON)
    blocked_topics = Column(JSON)
    enable_web_search = Column(Boolean, default=False)
    demo_mode_enabled = Column(Boolean, default=False)
    idle_timeout = Column(Integer, default=15)  # seconds of silence before auto-ending session
    video_quality = Column(String, default="auto")  # "auto" | "max"
    enable_video_generation = Column(Boolean, default=True)  # False = audio-only (no Lemon Slice)

    # API Keys (per-user, override global .env)
    openai_api_key = Column(String)
    deepgram_api_key = Column(String)
    elevenlabs_api_key = Column(String)
    lemonslice_api_key = Column(String)

    # TTS provider selection
    tts_provider = Column(String, default="openai")  # "openai" | "elevenlabs"

    # Plan / billing
    plan = Column(String, default="starter")  # starter / business / premium
    minutes_limit = Column(Integer, default=300)
    minutes_used = Column(Float, default=0.0)

    # Meta
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="companies")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="company", cascade="all, delete-orphan")
    dialogs = relationship("Dialog", back_populates="company", cascade="all, delete-orphan")
