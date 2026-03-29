import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    language = Column(String, default="ru")
    satisfaction_score = Column(Integer)  # 1-5
    topics = Column(JSON)  # ["цены", "запись", "расписание"]

    company = relationship("Company", back_populates="dialogs")
    messages = relationship("DialogMessage", back_populates="dialog", cascade="all, delete-orphan")


class DialogMessage(Base):
    __tablename__ = "dialog_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    dialog = relationship("Dialog", back_populates="messages")
