"""
RAG: semantic search over the company knowledge base stored in Qdrant.
"""
import logging
import os

from config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


async def search_knowledge_base(query: str, company_id: str, top_k: int = 5) -> str:
    """
    Search relevant chunks in the company knowledge base.
    Returns a formatted context string to inject into the system prompt.
    Returns empty string on any failure (agent continues without RAG context).
    """
    if not query and not company_id:
        return ""

    try:
        from qdrant_client import QdrantClient
        from openai import AsyncOpenAI

        qdrant = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=5,
        )
        collection_name = f"company_{company_id}"
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            logger.debug(f"No knowledge base for company {company_id}")
            return ""

        # Empty query → fetch all (for initial prompt building)
        if not query.strip():
            results = qdrant.scroll(
                collection_name=collection_name,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )[0]
            context = "\n\n".join(r.payload.get("text", "") for r in results)
            return context

        # Semantic search
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key or None)
        response = await openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query,
        )
        embedding = response.data[0].embedding

        results = qdrant.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=top_k,
            with_payload=True,
        )
        if not results:
            return ""

        context = "\n\n".join(hit.payload.get("text", "") for hit in results)
        return context

    except Exception as e:
        logger.debug(f"RAG search failed (non-critical): {e}")
        return ""
