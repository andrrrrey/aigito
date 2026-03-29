# AIGITO — AI Video Avatar for Offline Businesses

## Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

## Services

| Service  | Port | Description              |
|----------|------|--------------------------|
| backend  | 8000 | FastAPI REST API         |
| postgres | 5432 | PostgreSQL 16            |
| qdrant   | 6333 | Vector DB                |
| redis    | 6379 | Cache / sessions         |
| livekit  | 7880 | WebRTC media server      |
| nginx    | 80   | Reverse proxy            |

## Dev URLs

- API docs: http://localhost:8000/docs
- Admin panel: http://localhost/admin
- Kiosk: http://localhost/kiosk/{company-slug}

## Stack

- Backend: Python 3.11 / FastAPI
- Agent: LiveKit Agents SDK (Python) + openai, elevenlabs, lemonslice plugins
- Frontend: Vanilla JS + HTML
- DB: PostgreSQL + SQLAlchemy + Alembic
- Vector DB: Qdrant
- Cache: Redis
- LiveKit: self-hosted
