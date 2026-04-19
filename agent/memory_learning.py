"""
Self-learning service: extracts useful Q&A pairs from completed dialogs
and stores them in Qdrant so future sessions benefit from past conversations.

Learning is embedding-only (no extra LLM calls) — cheap and fast.
Deduplication prevents near-duplicate knowledge from accumulating.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.92  # skip if existing learned point is this similar
MIN_USER_MESSAGES = 2        # minimum user turns to consider learning
SOURCE_TYPE_LEARNED = "learned"

# Phrases that indicate the avatar didn't know the answer — skip these exchanges
NO_ANSWER_PHRASES = [
    "нет информации",
    "не знаю ответа",
    "не могу ответить",
    "оставьте ваш номер",
    "перезвонит вам",
    "i don't have information",
    "i cannot answer",
]

_qdrant_client = None
_openai_client = None


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        from config import settings
        _qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=10,
        )
    return _qdrant_client


def _get_openai(api_key: Optional[str] = None):
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        from config import settings
        _openai_client = AsyncOpenAI(api_key=api_key or settings.openai_api_key or None)
    return _openai_client


def _is_no_answer(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in NO_ANSWER_PHRASES)


def _build_qa_pairs(messages: list[dict]) -> list[str]:
    """
    Build Q&A text chunks from sequential (user, assistant) pairs.
    Skips pairs where the assistant said it doesn't know.
    """
    pairs = []
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]
        next_msg = messages[i + 1]
        if msg["role"] == "user" and next_msg["role"] == "assistant":
            user_text = msg["content"].strip()
            assistant_text = next_msg["content"].strip()
            if user_text and assistant_text and not _is_no_answer(assistant_text):
                pairs.append(f"Вопрос: {user_text}\nОтвет: {assistant_text}")
            i += 2
        else:
            i += 1
    return pairs


async def _is_duplicate(qdrant, collection_name: str, embedding: list[float]) -> bool:
    """Check if a very similar point already exists (learned or document)."""
    try:
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=1,
            with_payload=False,
            score_threshold=SIMILARITY_THRESHOLD,
        )
        return len(results) > 0
    except Exception as e:
        logger.warning("Duplicate check failed: %s", e)
        return False


async def learn_from_dialog(
    dialog_id: str,
    company_id: str,
    messages: list[dict],
    openai_key: Optional[str] = None,
):
    """
    Extract Q&A pairs from a completed dialog and store them in Qdrant.
    Called asynchronously from DialogTracker.finish() — must not block.
    """
    user_count = sum(1 for m in messages if m["role"] == "user")
    if user_count < MIN_USER_MESSAGES:
        logger.info(
            "memory_learning: skipping dialog=%s (only %d user messages)",
            dialog_id, user_count,
        )
        return

    pairs = _build_qa_pairs(messages)
    if not pairs:
        logger.info("memory_learning: no learnable pairs in dialog=%s", dialog_id)
        return

    logger.info(
        "memory_learning: dialog=%s company=%s extracted %d pairs",
        dialog_id, company_id, len(pairs),
    )

    try:
        from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

        qdrant = _get_qdrant()
        openai_client = _get_openai(openai_key)
        collection_name = f"company_{company_id}"

        # Ensure collection exists (it should already exist for any active company)
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            logger.warning(
                "memory_learning: collection %s not found, skipping",
                collection_name,
            )
            return

        # Embed all pairs in one batch
        response = await openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=pairs,
        )
        embeddings = [item.embedding for item in response.data]

        learned_at = datetime.now(timezone.utc).isoformat()
        points_to_add = []

        for pair_text, embedding in zip(pairs, embeddings):
            if await _is_duplicate(qdrant, collection_name, embedding):
                logger.debug("memory_learning: skipping duplicate pair for dialog=%s", dialog_id)
                continue
            points_to_add.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": pair_text,
                        "company_id": company_id,
                        "source_type": SOURCE_TYPE_LEARNED,
                        "dialog_id": dialog_id,
                        "learned_at": learned_at,
                    },
                )
            )

        if points_to_add:
            qdrant.upsert(collection_name=collection_name, points=points_to_add)
            logger.info(
                "memory_learning: stored %d new learned points for company=%s dialog=%s",
                len(points_to_add), company_id, dialog_id,
            )
        else:
            logger.info(
                "memory_learning: all pairs were duplicates for dialog=%s", dialog_id
            )

    except Exception:
        logger.exception(
            "memory_learning: failed for dialog=%s company=%s", dialog_id, company_id
        )


async def count_learned_points(company_id: str) -> int:
    """Count Qdrant points with source_type='learned' for a company."""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant = _get_qdrant()
        collection_name = f"company_{company_id}"
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            return 0

        result = qdrant.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value=SOURCE_TYPE_LEARNED))]
            ),
            exact=True,
        )
        return result.count
    except Exception as e:
        logger.warning("count_learned_points failed: %s", e)
        return 0


async def delete_learned_points(company_id: str) -> int:
    """Delete all learned points for a company. Returns number deleted."""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant = _get_qdrant()
        collection_name = f"company_{company_id}"
        existing = {c.name for c in qdrant.get_collections().collections}
        if collection_name not in existing:
            return 0

        before = qdrant.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value=SOURCE_TYPE_LEARNED))]
            ),
            exact=True,
        ).count

        qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value=SOURCE_TYPE_LEARNED))]
            ),
        )
        logger.info(
            "delete_learned_points: deleted %d points for company=%s", before, company_id
        )
        return before
    except Exception:
        logger.exception("delete_learned_points failed for company=%s", company_id)
        return 0
