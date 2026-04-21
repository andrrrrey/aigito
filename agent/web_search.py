"""
Web search via OpenAI Responses API (gpt-4o-mini-search-preview).
Fallback when the company knowledge base has no relevant results.
Uses the same OPENAI_API_KEY — no extra dependency or key needed.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)


async def search_web(query: str, api_key: str = "") -> str:
    """
    Ask OpenAI to search the web and return a plain-text summary.
    Returns empty string on failure or missing key.
    """
    effective_key = api_key or settings.openai_api_key or None
    if not effective_key:
        logger.warning("Web search skipped: no OpenAI API key available")
        return ""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=effective_key)
        response = await client.responses.create(
            model="gpt-4o-mini-search-preview",
            tools=[{"type": "web_search_preview"}],
            input=query,
        )
        parts = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for block in getattr(item, "content", []):
                    text = getattr(block, "text", "")
                    if text:
                        parts.append(text)

        context = "\n\n".join(parts)
        logger.info(
            "Web search: %d chars returned for query=%r",
            len(context), query[:80],
        )
        return context

    except Exception as e:
        logger.warning("Web search failed (non-critical): %s", e)
        return ""
