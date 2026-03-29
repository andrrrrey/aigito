"""
Test pipeline without frontend — checks connectivity to all services.
Usage: python scripts/test_pipeline.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


async def test_postgres():
    print("Testing PostgreSQL...", end=' ')
    try:
        import asyncpg
        db_url = os.getenv('DATABASE_URL', 'postgresql://aigita:aigita_dev_password@localhost:5432/aigita')
        # Convert asyncpg URL
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        conn = await asyncpg.connect(db_url)
        await conn.execute('SELECT 1')
        await conn.close()
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


async def test_redis():
    print("Testing Redis...", end=' ')
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        await r.ping()
        await r.aclose()
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


async def test_qdrant():
    print("Testing Qdrant...", end=' ')
    try:
        from qdrant_client import QdrantClient
        host = os.getenv('QDRANT_HOST', 'localhost')
        port = int(os.getenv('QDRANT_PORT', '6333'))
        client = QdrantClient(host=host, port=port, timeout=5)
        client.get_collections()
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


async def test_backend():
    print("Testing Backend API...", end=' ')
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.get('http://localhost:8000/health', timeout=5)
            assert res.status_code == 200
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


async def main():
    print("=" * 50)
    print("AIGITO Pipeline Test")
    print("=" * 50)

    results = await asyncio.gather(
        test_postgres(),
        test_redis(),
        test_qdrant(),
        test_backend(),
        return_exceptions=True,
    )

    passed = sum(1 for r in results if r is True)
    print(f"\nResults: {passed}/4 services healthy")
    sys.exit(0 if passed == 4 else 1)


asyncio.run(main())
