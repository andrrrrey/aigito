"""
Main AIGITO agent logic.
Pipeline: STT (ElevenLabs Scribe) → LLM (GPT-4o-mini) → TTS (ElevenLabs Flash) → Avatar (Lemon Slice)
"""
import json
import logging
from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import openai, elevenlabs
from rag import search_knowledge_base
from llm_router import get_llm
from prompt_builder import build_system_prompt
from config import settings

logger = logging.getLogger(__name__)


async def create_agent(ctx: agents.JobContext):
    await ctx.connect()
    logger.info(f"Agent connected to room: {ctx.room.name}")

    # Parse company config from room metadata
    company_id = "default"
    company_name = "AIGITO"
    location = "офисе"
    voice_id = None
    avatar_image_url = None

    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            company_id = meta.get("company_id", company_id)
            company_name = meta.get("company_name", company_name)
            location = meta.get("location_description", location)
            voice_id = meta.get("voice_id")
            avatar_image_url = meta.get("avatar_image_url")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Could not parse room metadata, using defaults")

    # Build system prompt (knowledge base injected at session start)
    knowledge_context = await search_knowledge_base("", company_id)
    system_prompt = build_system_prompt(
        company_name=company_name,
        location=location,
        knowledge_base=knowledge_context,
    )

    # STT — ElevenLabs Scribe v2 Realtime
    stt = elevenlabs.STT(
        model="scribe_v2",
        language="ru",
        api_key=settings.elevenlabs_api_key,
    )

    # TTS — ElevenLabs Flash
    tts_kwargs = dict(
        model="eleven_flash_v2_5",
        api_key=settings.elevenlabs_api_key,
    )
    if voice_id:
        tts_kwargs["voice_id"] = voice_id
    tts = elevenlabs.TTS(**tts_kwargs)

    # LLM
    llm = get_llm(company_id)

    # Avatar — Lemon Slice (Stage 2: enable when plugin available)
    avatar = None
    try:
        from livekit.plugins import lemonslice
        avatar = lemonslice.AvatarSession(
            agent_image_url=avatar_image_url,
            agent_prompt="professional, friendly, looking at camera, warm smile",
        )
    except ImportError:
        logger.warning("lemonslice plugin not available — running without video avatar")

    # Create agent session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
    )

    # Start avatar if available
    if avatar:
        await avatar.start(session, room=ctx.room)

    # Start session
    await session.start(
        room=ctx.room,
        agent=agents.Agent(instructions=system_prompt),
        room_input_options=RoomInputOptions(),
    )

    logger.info("Agent session started successfully")
