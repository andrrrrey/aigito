"""
Document ingestion pipeline: file → text chunks → embeddings → Qdrant.
Stage 1: skeleton only. Full implementation in Stage 3.
"""
import io
from typing import List


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from uploaded file bytes."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        return content.decode("utf-8", errors="ignore")
    # PDF, DOCX, CSV — placeholder for Stage 3
    return content.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


async def ingest_document(company_id: str, doc_id: str, text: str) -> int:
    """
    Embed chunks and upsert into Qdrant collection for the company.
    Returns the number of chunks ingested.
    Stage 1: stub — returns 0.
    """
    # Full implementation in Stage 3 (RAG)
    chunks = chunk_text(text)
    return len(chunks)
