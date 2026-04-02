"""
Main AIGITO agent logic — livekit-agents 1.5.1
Pipeline: STT (OpenAI Whisper) → LLM (GPT-4o-mini + RAG) → TTS (OpenAI)
Optional: Lemon Slice video avatar (if plugin installed)
"""
import asyncio
import json
import logging
import time
from typing import Optional

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
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

    # ── Diagnostic: log participants and tracks ────────────────────────────
    for pid, p in ctx.room.remote_participants.items():
        tracks = [(t.sid, t.kind, t.source) for t in p.track_publications.values()]
        logger.info("Remote participant: %s (identity=%s) tracks=%s", pid, p.identity, tracks)

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

    # ── Instantiate components (sync, fast) ───────────────────────────────────
    stt = lk_openai.STT(model="whisper-1", language="ru")

    OPENAI_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "sage", "coral"}
    tts_voice = voice_id if voice_id in OPENAI_VOICES else "nova"
    tts = lk_openai.TTS(model="tts-1", voice=tts_voice)

    llm = get_llm(company_id)

    tracker = DialogTracker(company_id=company_id)
    session_start = time.time()

    # ── Lemon Slice Avatar (optional, sync init) ────────────────────────────
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

    # ── Parallel initialization (RAG + DB + VAD) ────────────────────────────
    knowledge_context, _, vad = await asyncio.gather(
        search_knowledge_base("", company_id),
        tracker.start(),
        lk_silero.VAD.load(),
    )

    system_prompt = build_system_prompt(
        company_name=company_name,
        location=location,
        custom_rules=custom_rules,
        knowledge_base=knowledge_context,
    )

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
                asyncio.ensure_future(tracker.add_message(str(role), text.strip()))

    @session.on("close")
    def on_close(_event):
        duration = time.time() - session_start
        asyncio.ensure_future(tracker.finish(duration_seconds=duration))

    # ── Start avatar if available ─────────────────────────────────────────────
    if avatar:
        await avatar.start(session, room=ctx.room)

    # ── Start session ─────────────────────────────────────────────────────────
    await session.start(
        agent=Agent(instructions=system_prompt),
        room=ctx.room,
    )

    logger.info("Agent session started successfully")

    # ── Greeting ──────────────────────────────────────────────────────────────
    greeting = f"Здравствуйте! Я виртуальный ассистент компании {company_name}. Чем могу помочь?"
    logger.info("Sending greeting: %s", greeting)
    await session.say(greeting)
