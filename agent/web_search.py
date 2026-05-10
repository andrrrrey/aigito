"""
Web search via OpenAI Responses API with web_search_preview tool.
Works with standard gpt-4o-mini — no special search-preview model needed.
Fallback when the company knowledge base has no relevant results.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)

# Models to try in order — regular models support web_search_preview tool
_SEARCH_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4o-search-preview",
    "gpt-4o-mini-search-preview",
]


async def search_web(query: str, api_key: str = "") -> str:
    """
    Search the web via OpenAI Responses API and return a plain-text summary.
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
                if context:
                    logger.info(
                        "Web search (%s): %d chars for query=%r",
                        model, len(context), query[:80],
                    )
                    return context
                # Empty response — try next model
                last_error = ValueError(f"Empty response from {model}")
                continue

            except Exception as e:
                last_error = e
                err_str = str(e)
                if "not found" in err_str.lower() or "404" in err_str or "unsupported" in err_str.lower():
                    logger.debug("Web search model %s unavailable, trying next", model)
                    continue
                # Non-404 error — stop trying
                raise

        logger.warning("Web search: all models exhausted. Last error: %s", last_error)
        return ""

    except Exception as e:
        logger.warning("Web search failed (non-critical): %s", e)
        return ""
