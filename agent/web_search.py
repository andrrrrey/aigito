"""
Web search via OpenAI Responses API.
Fallback when the company knowledge base has no relevant results.
Uses the same OPENAI_API_KEY — no extra dependency or key needed.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)

# Try these models in order until one works
_SEARCH_MODELS = [
    "gpt-4o-search-preview",
    "gpt-4o-mini-search-preview",
]


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

        last_error = None
        for model in _SEARCH_MODELS:
            try:
                response = await client.responses.create(
                    model=model,
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
                    "Web search (%s): %d chars for query=%r",
                    model, len(context), query[:80],
                )
                return context
            except Exception as e:
                last_error = e
                if "not found" in str(e).lower() or "404" in str(e):
                    logger.debug("Web search model %s not available, trying next", model)
                    continue
                raise

        logger.warning("Web search failed (all models exhausted): %s", last_error)
        return ""

    except Exception as e:
        logger.warning("Web search failed (non-critical): %s", e)
        return ""
