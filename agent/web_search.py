"""
Web search via Tavily AI — fallback when KB has no relevant results.
Only called when enable_web_search=True and RAG returns empty context.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 3) -> str:
    """
    Search the web using Tavily API.
    Returns a formatted context string or empty string on failure/missing key.
    """
    if not settings.tavily_api_key:
        logger.warning("Web search requested but TAVILY_API_KEY is not configured")
        return ""

    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        results = response.get("results", [])
        if not results:
            logger.info("Web search: no results for query=%r", query[:80])
            return ""

        parts = []
        for r in results:
            title = r.get("title", "")
            content = r.get("content", "")
            if title or content:
                parts.append(f"[{title}]\n{content}" if title else content)

        context = "\n\n".join(parts)
        logger.info(
            "Web search: %d results, %d chars for query=%r",
            len(results), len(context), query[:80],
        )
        return context

    except Exception as e:
        logger.warning("Web search failed (non-critical): %s", e)
        return ""
