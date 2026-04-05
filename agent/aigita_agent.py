"""
Main AIGITO agent logic — livekit-agents 1.5.1
Pipeline: STT (Deepgram Nova-3) → LLM (GPT-5.4-mini + RAG) → TTS (OpenAI)
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
from livekit.plugins import deepgram as lk_deepgram
from livekit.plugins import silero as lk_silero

from rag import search_knowledge_base
from llm_router import get_llm
from prompt_builder import build_system_prompt, get_default_greeting
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
    video_quality = "auto"
    language = "ru"
    avatar_greeting = ""
    tts_provider = "openai"
    user_openai_api_key: Optional[str] = None
    user_deepgram_api_key: Optional[str] = None
    user_elevenlabs_api_key: Optional[str] = None
    user_lemonslice_api_key: Optional[str] = None

    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            company_id = meta.get("company_id", company_id)
            company_name = meta.get("company_name", company_name)
            location = meta.get("location_description", location)
            custom_rules = meta.get("custom_rules", "")
            voice_id = meta.get("voice_id")
            avatar_image_url = meta.get("avatar_image_url")
            video_quality = meta.get("video_quality", "auto")
            language = meta.get("language", "ru")
            avatar_greeting = meta.get("avatar_greeting", "")
            tts_provider = meta.get("tts_provider", "openai")
            user_openai_api_key = meta.get("openai_api_key") or None
            user_deepgram_api_key = meta.get("deepgram_api_key") or None
            user_elevenlabs_api_key = meta.get("elevenlabs_api_key") or None
            user_lemonslice_api_key = meta.get("lemonslice_api_key") or None
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Could not parse room metadata, using defaults")

    # ── Instantiate components (sync, fast) ───────────────────────────────────
    # Map language codes to Deepgram-supported language codes
    deepgram_lang_map = {"ru": "ru", "en": "en", "de": "de", "zh": "zh"}
    stt_language = deepgram_lang_map.get(language, "ru")

    # Resolve API keys: per-user override → global env fallback
    effective_openai_key = user_openai_api_key or settings.openai_api_key or None
    effective_deepgram_key = user_deepgram_api_key or settings.deepgram_api_key or None
    effective_elevenlabs_key = user_elevenlabs_api_key or settings.elevenlabs_api_key or None

    stt_kwargs = dict(model="nova-3", language=stt_language, interim_results=True)
    if effective_deepgram_key:
        stt_kwargs["api_key"] = effective_deepgram_key
    stt = lk_deepgram.STT(**stt_kwargs)

    # TTS: select provider based on company setting
    OPENAI_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "sage", "coral"}
    DEFAULT_ELEVENLABS_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    if tts_provider == "elevenlabs" and effective_elevenlabs_key:
        from livekit.plugins import elevenlabs as lk_elevenlabs

        # Guard: if voice_id is empty or is an OpenAI voice name, use ElevenLabs default
        el_voice_id = voice_id
        if not el_voice_id or el_voice_id in OPENAI_VOICES:
            logger.warning(
                "voice_id '%s' is missing or is an OpenAI voice; "
                "falling back to ElevenLabs default %s",
                voice_id, DEFAULT_ELEVENLABS_VOICE,
            )
            el_voice_id = DEFAULT_ELEVENLABS_VOICE

        try:
            tts = lk_elevenlabs.TTS(
                voice_id=el_voice_id,
                model="eleven_turbo_v2_5",
                language=language or "ru",
                encoding="pcm_24000",
                api_key=effective_elevenlabs_key,
            )
            logger.info(
                "Using ElevenLabs TTS (voice=%s, model=eleven_turbo_v2_5, lang=%s, encoding=pcm_24000)",
                el_voice_id, language,
            )
        except Exception as e:
            logger.error("ElevenLabs TTS init failed: %s — falling back to OpenAI", e)
            tts_voice = voice_id if voice_id in OPENAI_VOICES else "nova"
            tts_kwargs = dict(model="tts-1", voice=tts_voice)
            if effective_openai_key:
                tts_kwargs["api_key"] = effective_openai_key
            tts = lk_openai.TTS(**tts_kwargs)
    else:
        tts_voice = voice_id if voice_id in OPENAI_VOICES else "nova"
        tts_kwargs = dict(model="tts-1", voice=tts_voice)
        if effective_openai_key:
            tts_kwargs["api_key"] = effective_openai_key
        tts = lk_openai.TTS(**tts_kwargs)
        logger.info("Using OpenAI TTS (voice=%s)", tts_voice)

    llm = get_llm(company_id, api_key=effective_openai_key)

    tracker = DialogTracker(company_id=company_id)
    session_start = time.time()

    # ── Lemon Slice Avatar (optional, sync init) ────────────────────────────
    avatar = None
    effective_lemonslice_key = user_lemonslice_api_key or settings.lemonslice_api_key or None
    try:
        from livekit.plugins import lemonslice  # type: ignore
        if avatar_image_url:
            avatar_start_time = time.time()
            if video_quality == "max":
                vid_w, vid_h, vid_fps = 1024, 1024, 30
            else:
                vid_w, vid_h, vid_fps = 512, 512, 24
            avatar = lemonslice.AvatarSession(
                agent_image_url=avatar_image_url,
                agent_prompt="professional, friendly, looking at camera, warm smile",
                livekit_url=settings.livekit_public_url or settings.livekit_url,
                video_width=vid_w,
                video_height=vid_h,
                video_fps=vid_fps,
            )
            logger.info(
                "Lemon Slice avatar loaded in %.1fms (quality=%s, %dx%d@%dfps, url=%s)",
                (time.time() - avatar_start_time) * 1000,
                video_quality, vid_w, vid_h, vid_fps,
                settings.livekit_public_url or settings.livekit_url,
            )
        else:
            logger.info("No avatar_image_url, skipping LemonSlice")
    except (ImportError, TypeError) as e:
        logger.info("lemonslice plugin not available or config error: %s — running without video avatar", e)

    # ── VAD — Silero (sync load, must be before gather) ────────────────────
    vad = lk_silero.VAD.load(
        min_silence_duration=0.3,
        min_speech_duration=0.1,
        prefix_padding_duration=0.1,
        activation_threshold=0.5,
    )

    # ── Parallel initialization (RAG + DB) ──────────────────────────────────
    knowledge_context, _ = await asyncio.gather(
        search_knowledge_base("", company_id),
        tracker.start(),
    )

    system_prompt = build_system_prompt(
        company_name=company_name,
        location=location,
        custom_rules=custom_rules,
        knowledge_base=knowledge_context,
        language=language,
        avatar_greeting=avatar_greeting,
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
        try:
            avatar_connect_start = time.time()
            await avatar.start(session, room=ctx.room)
            logger.info("Lemon Slice avatar started in %.1fms", (time.time() - avatar_connect_start) * 1000)
        except Exception as e:
            logger.warning("Lemon Slice avatar failed, continuing without video: %s", e)
            avatar = None

    # ── Start session ─────────────────────────────────────────────────────────
    await session.start(
        agent=Agent(instructions=system_prompt),
        room=ctx.room,
    )

    logger.info("Agent session started successfully")

    # ── Greeting ──────────────────────────────────────────────────────────────
    if avatar_greeting and language == "ru":
        # Custom greeting in Russian — use as-is
        greeting = avatar_greeting
    elif avatar_greeting:
        # Custom greeting set in Russian, but user chose another language —
        # use the default translated greeting (LLM will handle translation in conversation)
        greeting = get_default_greeting(language, company_name)
    else:
        # No custom greeting — use language-appropriate default
        greeting = get_default_greeting(language, company_name)
    logger.info("Sending greeting (lang=%s): %s", language, greeting)
    await session.say(greeting)
