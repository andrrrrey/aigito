"""
RAG: search the company knowledge base via Qdrant.
Stage 1: stub returning empty context.
Full implementation in Stage 3.
"""
from config import settings


async def search_knowledge_base(query: str, company_id: str, top_k: int = 5) -> str:
    """
    Search relevant chunks in the company knowledge base.
    Returns a formatted context string to inject into the system prompt.
    """
    try:
        from qdrant_client import QdrantClient
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Get query embedding
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        embedding = response.data[0].embedding

        # Search in Qdrant
        collection_name = f"company_{company_id}"
        collections = [c.name for c in qdrant.get_collections().collections]
        if collection_name not in collections:
            return ""

        results = qdrant.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=top_k,
        )

        context = "\n\n".join([hit.payload.get("text", "") for hit in results])
        return context

    except Exception as e:
        # In Stage 1, Qdrant is empty — return empty context gracefully
        return ""
