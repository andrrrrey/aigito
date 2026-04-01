"""
Main AIGITO agent logic — livekit-agents 1.5.1
Pipeline: STT (OpenAI Whisper) → LLM (GPT-4o-mini + RAG) → TTS (OpenAI)
Optional: Lemon Slice video avatar (if plugin installed)
"""
import json
import logging
import time
from typing import Optional

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    ConversationItemAddedEvent,
)
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero as lk_silero

from rag import search_knowledge_base
from llm_router import get_llm
from prompt_builder import build_system_prompt
from dialog_tracker import DialogTracker
from config import settings

logger = logging.getLogger(__name__)


async def create_agent(ctx: JobContext):
    await ctx.connect()
    logger.info(f"Agent connected to room: {ctx.room.name}")

    # ── Parse company config from room metadata ──────────────────────────────
    company_id = "00000000-0000-0000-0000-000000000000"
    company_name = "AIGITO"
    location = "офисе компании"
    custom_rules = ""
    voice_id: Optional[str] = None
    avatar_image_url: Optional[str] = None

    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            company_id = meta.get("company_id", company_id)
            company_name = meta.get("company_name", company_name)
            location = meta.get("location_description", location)
            custom_rules = meta.get("custom_rules", "")
            voice_id = meta.get("voice_id")
            avatar_image_url = meta.get("avatar_image_url")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Could not parse room metadata, using defaults")

    # ── Build system prompt with initial RAG context ─────────────────────────
    knowledge_context = await search_knowledge_base("", company_id)
    system_prompt = build_system_prompt(
        company_name=company_name,
        location=location,
        custom_rules=custom_rules,
        knowledge_base=knowledge_context,
    )

    # ── STT — OpenAI Whisper ──────────────────────────────────────────────────
    stt = lk_openai.STT(
        model="whisper-1",
        language="ru",
    )

    # ── TTS — OpenAI ──────────────────────────────────────────────────────────
    tts_kwargs = dict(
        model="tts-1",
        voice="alloy",
    )
    if voice_id:
        tts_kwargs["voice"] = voice_id
    tts = lk_openai.TTS(**tts_kwargs)

    # ── LLM — GPT-4o-mini ────────────────────────────────────────────────────
    llm = get_llm(company_id)

    # ── Lemon Slice Avatar (optional) ───────────────────────────────────────
    avatar = None
    try:
        from livekit.plugins import lemonslice  # type: ignore
        if avatar_image_url:
            avatar = lemonslice.AvatarSession(
                agent_image_url=avatar_image_url,
                agent_prompt="professional, friendly, looking at camera, warm smile",
                livekit_url=settings.livekit_public_url or settings.livekit_url,
            )
            logger.info("Lemon Slice avatar plugin loaded (url=%s)", settings.livekit_public_url or settings.livekit_url)
        else:
            logger.info("No avatar_image_url, skipping LemonSlice")
    except (ImportError, TypeError) as e:
        logger.info("lemonslice plugin not available or config error: %s — running without video avatar", e)
        avatar = None

    # ── Dialog tracking ───────────────────────────────────────────────────────
    tracker = DialogTracker(company_id=company_id)
    session_start = time.time()
    await tracker.start()

    # ── VAD — Silero (required for non-streaming STT) ──────────────────────
    vad = lk_silero.VAD.load()

    # ── AgentSession ─────────────────────────────────────────────────────────
    session = AgentSession(
        vad=vad,
        stt=stt,
        llm=llm,
        tts=tts,
    )

    # Subscribe to conversation events for dialog recording
    @session.on("conversation_item_added")
    def on_conversation_item(event: ConversationItemAddedEvent):
        item = event.item
        role = getattr(item, "role", None)
        content_parts = getattr(item, "content", [])
        if role and content_parts:
            text = " ".join(
                part.text if hasattr(part, "text") else str(part)
                for part in content_parts
                if part
            )
            if text.strip():
                import asyncio
                asyncio.ensure_future(tracker.add_message(str(role), text.strip()))

    @session.on("close")
    def on_close(_event):
        duration = time.time() - session_start
        import asyncio
        asyncio.ensure_future(tracker.finish(duration_seconds=duration))

    # ── Start avatar if available ─────────────────────────────────────────────
    if avatar:
        await avatar.start(session, room=ctx.room)

    # ── Start session ─────────────────────────────────────────────────────────
    await session.start(
        agent=Agent(instructions=system_prompt),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
    )

    logger.info("Agent session started successfully")
