"""
AIGITO integration test — checks all services are healthy.
Usage:
  # From docker-compose network:
  docker compose exec backend python /scripts/test_pipeline.py

  # Locally (with services accessible on localhost):
  python scripts/test_pipeline.py
"""
import asyncio
import os
import sys
import time

# Allow overriding service hosts for local testing
PG_URL   = os.getenv("DATABASE_URL",  "postgresql://aigita:aigita_dev_password@localhost:5432/aigita")
REDIS_URL = os.getenv("REDIS_URL",    "redis://localhost:6379")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LK_URL = os.getenv("LIVEKIT_URL",    "http://localhost:7880")


def ok(name): print(f"  \033[92m✓\033[0m  {name}")
def fail(name, err): print(f"  \033[91m✗\033[0m  {name}: {err}")


async def test_postgres() -> bool:
    try:
        import asyncpg
        url = PG_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url, timeout=5)
        await conn.fetchval("SELECT 1")
        await conn.close()
        # Check tables exist
        conn = await asyncpg.connect(url, timeout=5)
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        )
        table_names = {r["tablename"] for r in tables}
        required = {"users", "companies", "dialogs", "dialog_messages", "knowledge_documents"}
        missing = required - table_names
        await conn.close()
        if missing:
            fail("PostgreSQL", f"Missing tables: {missing}")
            return False
        ok(f"PostgreSQL (tables: {', '.join(sorted(table_names))})")
        return True
    except Exception as e:
        fail("PostgreSQL", e)
        return False


async def test_redis() -> bool:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(REDIS_URL, socket_timeout=5)
        pong = await r.ping()
        await r.aclose()
        ok(f"Redis (ping: {pong})")
        return True
    except Exception as e:
        fail("Redis", e)
        return False


async def test_qdrant() -> bool:
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
        collections = client.get_collections().collections
        ok(f"Qdrant ({len(collections)} collections)")
        return True
    except Exception as e:
        fail("Qdrant", e)
        return False


async def test_backend() -> bool:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            # Health check
            r = await client.get(f"{BACKEND_URL}/health")
            assert r.status_code == 200, f"status={r.status_code}"
            ok(f"Backend /health → {r.json()}")

            # Swagger docs accessible
            r2 = await client.get(f"{BACKEND_URL}/docs")
            assert r2.status_code == 200
            ok("Backend /docs (Swagger UI)")
        return True
    except Exception as e:
        fail("Backend", e)
        return False


async def test_livekit() -> bool:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(LK_URL)
            # LiveKit returns 404 or 200 on root — both mean server is up
            ok(f"LiveKit server (status={r.status_code})")
        return True
    except Exception as e:
        fail("LiveKit", e)
        return False


async def test_rag_ingest() -> bool:
    """Test document ingest pipeline (requires OpenAI key)."""
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key or openai_key.startswith("placeholder"):
        ok("RAG ingest (skipped — no OPENAI_API_KEY)")
        return True
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from knowledge.ingest import chunk_text, extract_text
        sample = "Консультация стоматолога: 1500 руб. Чистка зубов: 4500 руб."
        chunks = chunk_text(sample)
        assert len(chunks) >= 1
        ok(f"RAG chunk_text ({len(chunks)} chunks)")
        return True
    except Exception as e:
        fail("RAG ingest", e)
        return False


async def main():
    print("\n" + "=" * 55)
    print("  AIGITO Pipeline Test")
    print("=" * 55 + "\n")

    start = time.time()
    results = await asyncio.gather(
        test_postgres(),
        test_redis(),
        test_qdrant(),
        test_backend(),
        test_livekit(),
        test_rag_ingest(),
        return_exceptions=True,
    )

    passed = sum(1 for r in results if r is True)
    total = len(results)
    elapsed = time.time() - start

    print(f"\n{'=' * 55}")
    print(f"  Result: {passed}/{total} tests passed ({elapsed:.1f}s)")
    print("=" * 55 + "\n")

    if passed < total:
        print("Some services are not ready. Check docker-compose logs.")
        sys.exit(1)
    else:
        print("All services healthy. AIGITO is ready!")


asyncio.run(main())
