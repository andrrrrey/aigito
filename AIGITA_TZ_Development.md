# AIGITA — Техническое задание для разработки MVP
## Версия 1.0 | Для исполнения в Claude Code

---

# 1. ОБЗОР ПРОЕКТА

## 1.1 Что делаем

Веб-приложение AI видео-аватар для оффлайн бизнесов. Клиент подходит к экрану (планшет/ТВ/киоск), аватар его слушает, обрабатывает вопрос через LLM + базу знаний компании, отвечает голосом с реалистичной мимикой и lip-sync.

## 1.2 Стек технологий

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| **STT** | ElevenLabs Scribe v2 Realtime | Распознавание речи клиента |
| **LLM** | GPT-4o-mini (основной) + GPT-4o (fallback) | Генерация ответа по базе знаний |
| **TTS** | ElevenLabs Flash/Turbo | Синтез голоса аватара |
| **Видео** | Lemon Slice Self-Managed API | Генерация видео аватара (lip-sync, мимика) |
| **Оркестрация** | LiveKit Agents (Python SDK) | Связка всех компонентов в realtime pipeline |
| **Бэкенд** | Python 3.11+ / FastAPI | API, админка, управление базой знаний |
| **Фронтенд (киоск)** | Vanilla JS + HTML | Интерфейс на экране клиента |
| **Фронтенд (админка)** | Vanilla JS + HTML | Личный кабинет владельца бизнеса |
| **БД** | PostgreSQL | Данные компаний, диалоги, аналитика |
| **Векторная БД** | Qdrant | Хранение и поиск по базе знаний (RAG) |
| **Кэш/очереди** | Redis | Сессии, rate limiting, очередь задач |
| **Деплой** | Docker Compose на VPS | Ubuntu 22.04+, 4+ CPU, 8+ GB RAM |

## 1.3 Архитектура (упрощённая)

```
┌─────────────────────────────────────────────────────┐
│                   КЛИЕНТСКИЙ ЭКРАН                    │
│              (браузер, Vanilla JS)                    │
│                                                       │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ Микрофон │  │ Видео     │  │ Chips/подсказки  │  │
│  │ (WebRTC) │  │ аватара   │  │                  │  │
│  └────┬─────┘  └─────▲─────┘  └──────────────────┘  │
│       │              │                                │
└───────┼──────────────┼────────────────────────────────┘
        │              │
        ▼              │
┌───────────────────────────────────────────────────────┐
│                   LIVEKIT SERVER                       │
│              (WebRTC media transport)                  │
└───────┬──────────────▲────────────────────────────────┘
        │              │
        ▼              │
┌───────────────────────────────────────────────────────┐
│               LIVEKIT AGENT (Python)                   │
│                                                       │
│  ┌─────────┐   ┌─────────┐   ┌─────────────────────┐ │
│  │ STT     │   │ LLM     │   │ TTS                 │ │
│  │ElevenLabs│──▶│GPT-4o-  │──▶│ ElevenLabs Flash   │ │
│  │ Scribe  │   │ mini    │   │                     │ │
│  └─────────┘   └────┬────┘   └──────────┬──────────┘ │
│                     │                    │            │
│                     ▼                    ▼            │
│              ┌──────────┐    ┌────────────────────┐   │
│              │ RAG      │    │ Lemon Slice API    │   │
│              │ (Qdrant) │    │ (видео аватара)    │   │
│              └──────────┘    └────────────────────┘   │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND                        │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐│
│  │ Auth     │  │ Admin API│  │ Analytics            ││
│  │ (JWT)    │  │ (CRUD)   │  │ (диалоги, минуты)   ││
│  └──────────┘  └──────────┘  └──────────────────────┘│
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐│
│  │PostgreSQL│  │ Qdrant   │  │ Redis               ││
│  └──────────┘  └──────────┘  └──────────────────────┘│
└───────────────────────────────────────────────────────┘
```

---

# 2. НЕОБХОДИМЫЕ API-КЛЮЧИ И АККАУНТЫ

Перед началом разработки получить:

1. **Lemon Slice API key** — https://lemonslice.com/agents/api
2. **ElevenLabs API key** — https://elevenlabs.io/app/settings/api-keys (план Pro или Scale)
3. **OpenAI API key** — https://platform.openai.com/api-keys
4. **LiveKit Server** — self-hosted, входит в docker-compose. Ключи задаются вручную в `livekit.yaml` — регистрация нигде не нужна
5. **VPS** — Ubuntu 22.04, 4 CPU, 8 GB RAM, 50 GB SSD

---

# 3. СТРУКТУРА ПРОЕКТА

```
aigita/
├── docker-compose.yml
├── livekit.yaml                    # Конфиг LiveKit Server (ключи задаются здесь)
├── .env.example
├── README.md
│
├── agent/                          # LiveKit Agent (ядро пайплайна)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # Точка входа LiveKit Agent
│   ├── aigita_agent.py             # Основная логика агента
│   ├── rag.py                      # RAG: поиск по базе знаний через Qdrant
│   ├── llm_router.py               # Роутинг GPT-4o-mini / GPT-4o
│   ├── prompt_builder.py           # Сборка системного промпта
│   └── config.py                   # Конфигурация из .env
│
├── backend/                        # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # Точка входа FastAPI
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py               # /auth/login, /auth/register
│   │   ├── models.py               # User model
│   │   └── jwt.py                  # JWT utils
│   ├── companies/
│   │   ├── __init__.py
│   │   ├── router.py               # CRUD компаний
│   │   ├── models.py               # Company, Avatar models
│   │   └── schemas.py              # Pydantic schemas
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── router.py               # Загрузка/управление базой знаний
│   │   ├── ingest.py               # Парсинг документов → chunks → Qdrant
│   │   └── models.py               # KnowledgeDocument model
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── router.py               # API аналитики
│   │   └── models.py               # Dialog, DialogMessage models
│   ├── kiosk/
│   │   ├── __init__.py
│   │   └── router.py               # API для киоска (получить конфиг аватара)
│   ├── database.py                 # SQLAlchemy setup
│   └── config.py
│
├── frontend-kiosk/                 # Клиентский экран (киоск/планшет)
│   ├── index.html                  # Основная страница
│   ├── style.css                   # Стили
│   ├── app.js                      # Основная логика
│   ├── livekit-client.js           # LiveKit WebRTC клиент
│   └── ui.js                       # UI компоненты (chips, waveform, состояния)
│
├── frontend-admin/                 # Админка (личный кабинет)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── pages/
│   │   ├── dashboard.html          # Дашборд с аналитикой
│   │   ├── knowledge.html          # Управление базой знаний
│   │   ├── avatar.html             # Настройки аватара
│   │   └── settings.html           # Настройки компании
│   └── api.js                      # Обёртка над backend API
│
├── nginx/
│   ├── nginx.conf                  # Reverse proxy
│   └── Dockerfile
│
└── scripts/
    ├── init_db.py                  # Инициализация БД
    ├── seed_demo.py                # Демо-данные (клиника, автосалон)
    └── test_pipeline.py            # Тест пайплайна без фронтенда
```

---

# 4. КОМПОНЕНТЫ — ДЕТАЛЬНОЕ ОПИСАНИЕ

## 4.1 LiveKit Agent (agent/)

Это ядро всей системы. LiveKit Agent — Python-процесс, который:
1. Получает аудио-поток от клиента через WebRTC
2. Передаёт аудио в STT (ElevenLabs Scribe Realtime)
3. Отправляет распознанный текст в LLM (GPT-4o-mini)
4. Получает ответ, отправляет в TTS (ElevenLabs Flash)
5. Аудио TTS автоматически синхронизируется с видео Lemon Slice
6. Видео-поток аватара отправляется обратно клиенту через WebRTC

### main.py — точка входа

```python
from livekit import agents
from aigita_agent import create_agent

# LiveKit Agents entrypoint
app = agents.WorkerOptions(
    entrypoint_fnc=create_agent,
)

if __name__ == "__main__":
    agents.cli.run_app(app)
```

### aigita_agent.py — основная логика

```python
from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import openai, elevenlabs, lemonslice
from rag import search_knowledge_base
from llm_router import get_llm
from prompt_builder import build_system_prompt

async def create_agent(ctx: agents.JobContext):
    await ctx.connect()
    
    # Получить конфиг компании из метаданных комнаты
    room_metadata = ctx.room.metadata  # JSON с company_id, avatar_config
    company_config = json.loads(room_metadata)
    company_id = company_config["company_id"]
    
    # Построить системный промпт с базой знаний
    system_prompt = build_system_prompt(company_id)
    
    # Настроить LLM с RAG
    llm = get_llm(company_id)
    
    # Настроить STT
    stt = elevenlabs.STT(
        model="scribe_v2",
        language="ru",
    )
    
    # Настроить TTS
    tts = elevenlabs.TTS(
        model="eleven_flash_v2_5",
        voice_id=company_config.get("voice_id", "default_russian_voice"),
    )
    
    # Настроить аватар
    avatar = lemonslice.AvatarSession(
        agent_image_url=company_config.get("avatar_image_url"),
        agent_prompt="professional, friendly, looking at camera, warm smile",
    )
    
    # Создать сессию агента
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
    )
    
    # Запустить аватар
    await avatar.start(session, room=ctx.room)
    
    # Запустить сессию
    await session.start(
        room=ctx.room,
        agent=agents.Agent(instructions=system_prompt),
    )
```

### rag.py — поиск по базе знаний

```python
from qdrant_client import QdrantClient
from openai import OpenAI

client = QdrantClient(host="qdrant", port=6333)
openai_client = OpenAI()

async def search_knowledge_base(query: str, company_id: str, top_k: int = 5) -> str:
    """Поиск релевантных фрагментов в базе знаний компании."""
    
    # Получить эмбеддинг запроса
    embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    
    # Поиск в Qdrant
    results = client.search(
        collection_name=f"company_{company_id}",
        query_vector=embedding,
        limit=top_k,
    )
    
    # Собрать контекст
    context = "\n\n".join([hit.payload["text"] for hit in results])
    return context
```

### llm_router.py — роутинг между моделями

```python
from livekit.plugins import openai

def get_llm(company_id: str):
    """
    Основная модель — GPT-4o-mini (дешёвая, быстрая).
    Для сложных вопросов можно переключить на GPT-4o
    через настройки в админке.
    """
    return openai.LLM(
        model="gpt-4o-mini",
        temperature=0.3,  # Низкая — чтобы не фантазировал
    )
```

### prompt_builder.py — системный промпт

```python
from rag import search_knowledge_base

def build_system_prompt(company_id: str) -> str:
    """Строит системный промпт для конкретной компании."""
    
    # Базовый промпт AIGITA
    base_prompt = """
Ты — AI-консультант компании {company_name}. 
Ты работаешь на экране в {location} и помогаешь клиентам.

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленной базы знаний.
2. Если не знаешь ответ — скажи: "К сожалению, у меня нет информации по этому вопросу. 
   Оставьте ваш номер телефона, и наш специалист перезвонит вам."
3. НИКОГДА не выдумывай информацию, цены, расписание.
4. Будь приветливым и профессиональным.
5. Отвечай кратко — 2-3 предложения максимум. Ты разговариваешь голосом.
6. Говори на языке клиента — если он говорит по-русски, отвечай по-русски.
7. {custom_rules}

БАЗА ЗНАНИЙ КОМПАНИИ:
{knowledge_base}
"""
    
    # Загрузить конфиг компании из БД
    company = get_company(company_id)
    
    return base_prompt.format(
        company_name=company.name,
        location=company.location_description,
        custom_rules=company.custom_rules or "",
        knowledge_base=company.knowledge_summary,
    )
```

## 4.2 FastAPI Backend (backend/)

### main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.router import router as auth_router
from companies.router import router as companies_router
from knowledge.router import router as knowledge_router
from analytics.router import router as analytics_router
from kiosk.router import router as kiosk_router

app = FastAPI(title="AIGITA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # На проде — ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(companies_router, prefix="/api/companies", tags=["companies"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(kiosk_router, prefix="/api/kiosk", tags=["kiosk"])
```

### Ключевые endpoints

```
AUTH:
POST /api/auth/register          — регистрация
POST /api/auth/login             — логин (возвращает JWT)

COMPANIES:
GET    /api/companies/me         — данные своей компании
PUT    /api/companies/me         — обновить настройки
PUT    /api/companies/me/avatar  — настройки аватара (image_url, voice_id, prompt)
PUT    /api/companies/me/rules   — правила поведения аватара

KNOWLEDGE BASE:
GET    /api/knowledge/documents           — список документов
POST   /api/knowledge/documents/upload    — загрузить документ (PDF, DOCX, TXT, CSV)
DELETE /api/knowledge/documents/{id}      — удалить документ
POST   /api/knowledge/rebuild             — пересобрать индекс Qdrant

KIOSK (вызывается с экрана клиента):
GET    /api/kiosk/{company_slug}/config   — получить конфиг для LiveKit
POST   /api/kiosk/{company_slug}/token    — получить LiveKit token для подключения

ANALYTICS:
GET    /api/analytics/summary             — сводка (диалоги, минуты, темы)
GET    /api/analytics/dialogs             — список диалогов с фильтрами
GET    /api/analytics/topics              — топ тем вопросов
GET    /api/analytics/usage               — расход минут
```

### Модели БД (SQLAlchemy)

```python
# companies/models.py

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)  # для URL киоска
    
    # Настройки аватара
    avatar_image_url = Column(String)        # URL изображения для Lemon Slice
    avatar_voice_id = Column(String)         # ElevenLabs voice ID
    avatar_prompt = Column(Text)             # Промпт для демонра аватара
    location_description = Column(String)    # "зона ожидания стоматологии"
    
    # Правила
    custom_rules = Column(Text)              # Доп. правила для LLM
    allowed_topics = Column(JSON)            # Разрешённые темы
    blocked_topics = Column(JSON)            # Запрещённые темы
    enable_web_search = Column(Boolean, default=False)
    
    # Тариф
    plan = Column(String, default="starter") # starter / business / premium
    minutes_limit = Column(Integer, default=300)
    minutes_used = Column(Float, default=0)
    
    # Мета
    created_at = Column(DateTime, default=func.now())
    owner_id = Column(UUID, ForeignKey("users.id"))


class Dialog(Base):
    __tablename__ = "dialogs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"))
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    duration_seconds = Column(Float)
    language = Column(String, default="ru")
    satisfaction_score = Column(Integer)      # 1-5, если клиент оценил
    topics = Column(JSON)                     # ["цены", "запись", "расписание"]
    

class DialogMessage(Base):
    __tablename__ = "dialog_messages"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    dialog_id = Column(UUID, ForeignKey("dialogs.id"))
    role = Column(String)                     # "user" или "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"))
    filename = Column(String)
    file_type = Column(String)               # pdf, docx, txt, csv
    content_text = Column(Text)              # Извлечённый текст
    chunks_count = Column(Integer)
    uploaded_at = Column(DateTime, default=func.now())
```

## 4.3 Frontend — Киоск (frontend-kiosk/)

### index.html — основная структура

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIGITA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="app">
        <!-- Состояние: ожидание -->
        <div id="screen-idle" class="screen active">
            <div id="avatar-idle-video"></div>
            <div class="idle-prompt">
                <h2>Здравствуйте! Я могу вам помочь.</h2>
                <p>Нажмите кнопку и задайте вопрос</p>
            </div>
            <button id="btn-start" class="btn-mic btn-mic-large">
                <svg><!-- микрофон --></svg>
            </button>
        </div>
        
        <!-- Состояние: диалог -->
        <div id="screen-dialog" class="screen">
            <div id="avatar-video-container">
                <video id="avatar-video" autoplay playsinline></video>
                <div id="status-indicator"></div>
            </div>
            
            <!-- Субтитры -->
            <div id="subtitles"></div>
            
            <!-- Chips подсказки -->
            <div id="chips-container">
                <button class="chip" data-text="Какие услуги вы предлагаете?">Какие услуги?</button>
                <button class="chip" data-text="Сколько стоит консультация?">Сколько стоит?</button>
                <button class="chip" data-text="Запишите меня на приём">Записаться</button>
            </div>
            
            <!-- Кнопка микрофона -->
            <div id="mic-controls">
                <div id="waveform-left" class="waveform"></div>
                <button id="btn-mic" class="btn-mic">
                    <svg><!-- микрофон --></svg>
                </button>
                <div id="waveform-right" class="waveform"></div>
            </div>
            
            <!-- Кнопка завершить -->
            <button id="btn-end" class="btn-end">Завершить</button>
        </div>
    </div>
    
    <script src="https://cdn.livekit.io/livekit-client/latest/livekit-client.umd.js"></script>
    <script src="app.js"></script>
</body>
</html>
```

### app.js — основная логика

```javascript
const AIGITA = {
    room: null,
    companySlug: null,
    state: 'idle', // idle | connecting | listening | thinking | speaking
    
    async init() {
        // Получить slug компании из URL: /kiosk/dental-smile
        this.companySlug = window.location.pathname.split('/').pop();
        
        // Загрузить конфиг компании
        const config = await this.loadConfig();
        this.applyConfig(config);
        
        // Слушать кнопку старта
        document.getElementById('btn-start').addEventListener('click', () => this.startDialog());
        document.getElementById('btn-end').addEventListener('click', () => this.endDialog());
        
        // Chips
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => this.sendText(chip.dataset.text));
        });
    },
    
    async loadConfig() {
        const res = await fetch(`/api/kiosk/${this.companySlug}/config`);
        return res.json();
    },
    
    async startDialog() {
        this.setState('connecting');
        
        // Получить LiveKit token
        const res = await fetch(`/api/kiosk/${this.companySlug}/token`, {
            method: 'POST'
        });
        const { token, url } = await res.json();
        
        // Подключиться к LiveKit комнате
        this.room = new LivekitClient.Room();
        
        this.room.on('trackSubscribed', (track, publication, participant) => {
            if (track.kind === 'video') {
                const videoEl = document.getElementById('avatar-video');
                track.attach(videoEl);
            }
            if (track.kind === 'audio') {
                const audioEl = new Audio();
                track.attach(audioEl);
            }
        });
        
        await this.room.connect(url, token);
        
        // Включить микрофон
        await this.room.localParticipant.setMicrophoneEnabled(true);
        
        this.setState('listening');
    },
    
    async endDialog() {
        if (this.room) {
            await this.room.disconnect();
            this.room = null;
        }
        this.setState('idle');
    },
    
    setState(state) {
        this.state = state;
        // Обновить UI в зависимости от состояния
        document.getElementById('screen-idle').classList.toggle('active', state === 'idle');
        document.getElementById('screen-dialog').classList.toggle('active', state !== 'idle');
        
        const indicator = document.getElementById('status-indicator');
        indicator.className = `status-${state}`;
    },
    
    async sendText(text) {
        // Отправить текстовое сообщение через LiveKit data channel
        if (this.room) {
            const encoder = new TextEncoder();
            await this.room.localParticipant.publishData(
                encoder.encode(JSON.stringify({ type: 'text', content: text })),
                { reliable: true }
            );
        }
    }
};

document.addEventListener('DOMContentLoaded', () => AIGITA.init());
```

## 4.4 Frontend — Админка (frontend-admin/)

Минимальный личный кабинет для MVP:

### Страницы:

**dashboard.html** — дашборд:
- Карточки: «Диалогов сегодня», «Минут осталось», «Ср. длительность», «Удовлетворённость»
- График диалогов за 30 дней (Chart.js)
- Топ-5 тем вопросов

**knowledge.html** — база знаний:
- Список загруженных документов
- Кнопка «Загрузить документ» (drag-and-drop)
- Кнопка «Пересобрать индекс»

**avatar.html** — настройки аватара:
- Загрузка/смена изображения аватара
- Выбор голоса (dropdown с preview)
- Текстовое поле: кастомные правила поведения
- Текстовое поле: запрещённые темы
- Чекбокс: разрешить веб-поиск

**settings.html** — настройки:
- Название компании, slug
- Тарифный план и расход минут (прогресс-бар)

---

# 5. DOCKER COMPOSE

```yaml
version: "3.9"

services:
  # === Базы данных ===
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: aigita
      POSTGRES_USER: aigita
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # === LiveKit Server (self-hosted, ключи в livekit.yaml) ===
  livekit:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit.yaml
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    ports:
      - "7880:7880"   # HTTP
      - "7881:7881"   # WebRTC TCP
      - "7882:7882"   # WebRTC TCP (TLS)

  # === AIGITA Agent ===
  agent:
    build: ./agent
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - LEMONSLICE_API_KEY=${LEMONSLICE_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/aigita
    depends_on:
      - livekit
      - qdrant
      - postgres

  # === FastAPI Backend ===
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/aigita
      - REDIS_URL=redis://redis:6379
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - postgres
      - redis
      - qdrant
    ports:
      - "8000:8000"

  # === Nginx ===
  nginx:
    build: ./nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - livekit
    volumes:
      - ./frontend-kiosk:/usr/share/nginx/html/kiosk
      - ./frontend-admin:/usr/share/nginx/html/admin

volumes:
  pgdata:
  qdrant_data:
```

---

# 6. .env.example

```env
# === Database ===
POSTGRES_USER=aigita
POSTGRES_PASSWORD=your_secure_password_here

# === LiveKit (self-hosted, ключи задаёшь сам — должны совпадать с livekit.yaml) ===
LIVEKIT_API_KEY=aigita_dev_key
LIVEKIT_API_SECRET=aigita_dev_secret_change_me
LIVEKIT_URL=ws://livekit:7880

# === OpenAI ===
OPENAI_API_KEY=sk-your-openai-key

# === ElevenLabs ===
ELEVENLABS_API_KEY=your_elevenlabs_key

# === Lemon Slice ===
LEMONSLICE_API_KEY=your_lemonslice_key

# === App ===
JWT_SECRET=your_jwt_secret_here
ENVIRONMENT=development
```

## 6.1 livekit.yaml

LiveKit Server self-hosted — регистрация нигде не нужна. Ключи задаются прямо в этом файле и должны совпадать с `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` из `.env`.

```yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
keys:
  aigita_dev_key: aigita_dev_secret_change_me
logging:
  level: info
```

На проде — заменить ключи на длинные случайные строки и добавить `turn` секцию для NAT traversal.

---

# 7. ПОРЯДОК РАЗРАБОТКИ (ЭТАПЫ)

## Этап 1: Инфраструктура (день 1)
- [ ] Создать проект, структуру папок
- [ ] Создать `livekit.yaml` с ключами, `.env` из `.env.example`
- [ ] Настроить docker-compose (postgres, qdrant, redis, livekit)
- [ ] Создать модели БД (SQLAlchemy), alembic миграции
- [ ] Запустить всё локально, проверить что контейнеры работают

## Этап 2: LiveKit Agent — базовый пайплайн (дни 2-3)
- [ ] Установить livekit-agents, плагины (openai, elevenlabs, lemonslice)
- [ ] Создать минимальный agent — STT → LLM → TTS → Lemon Slice
- [ ] Протестировать через LiveKit Playground (https://agents-playground.livekit.io)
- [ ] Добиться работающего цикла: говоришь в микрофон → аватар отвечает

## Этап 3: RAG и база знаний (день 4)
- [ ] Реализовать ingestion pipeline: документ → chunks → embeddings → Qdrant
- [ ] Интегрировать RAG в агента (поиск перед ответом LLM)
- [ ] Создать тестовую базу знаний (демо-клиника)
- [ ] Протестировать: вопрос о цене → ответ из базы знаний

## Этап 4: Backend API (дни 5-6)
- [ ] Auth (register, login, JWT)
- [ ] CRUD компаний
- [ ] Upload/управление документами базы знаний
- [ ] Kiosk API (конфиг + LiveKit token)
- [ ] Аналитика (запись диалогов, подсчёт минут)

## Этап 5: Frontend — Киоск (день 7)
- [ ] Базовый UI: idle-экран → кнопка → диалог
- [ ] LiveKit WebRTC подключение
- [ ] Видео аватара + аудио
- [ ] Состояния (idle, connecting, listening, speaking)
- [ ] Chips-подсказки

## Этап 6: Frontend — Админка (день 8)
- [ ] Дашборд с метриками
- [ ] Загрузка документов
- [ ] Настройки аватара
- [ ] Расход минут

## Этап 7: Деплой на VPS (день 9)
- [ ] Развернуть docker-compose на VPS
- [ ] Настроить nginx + SSL (Let's Encrypt)
- [ ] Настроить домен
- [ ] Проверить работу через браузер

## Этап 8: Тестирование и полировка (день 10)
- [ ] Тест полного цикла: открыть URL на планшете → поговорить
- [ ] Замерить латентность (цель: < 2 сек от вопроса до начала ответа)
- [ ] Исправить баги
- [ ] Записать демо-видео

---

# 8. ТРЕБОВАНИЯ К VPS

**Минимальные:**
- Ubuntu 22.04 LTS
- 4 vCPU
- 8 GB RAM
- 50 GB SSD
- Docker + Docker Compose
- Открытые порты: 80, 443, 7880-7882 (LiveKit WebRTC)

**Рекомендуемые для прода:**
- 8 vCPU
- 16 GB RAM
- 100 GB SSD
- Отдельный домен с SSL

---

# 9. ДЕМО-СЦЕНАРИЙ ДЛЯ ТЕСТИРОВАНИЯ

## Демо-компания: «Стоматология Улыбка»

**База знаний:**
- Прайс-лист: консультация 1500₽, чистка 4500₽, пломба от 3500₽, виниры от 25000₽
- Врачи: Иванова А.С. (терапевт, пн-пт 9-18), Петров К.М. (ортодонт, вт-чт 10-19)
- Подготовка: не есть за 2 часа до визита, взять паспорт и полис
- Адрес: ул. Ленина 42, 2 этаж, вход со двора
- Время работы: пн-пт 9-20, сб 10-16, вс выходной

**Тестовые вопросы:**
1. «Сколько стоит поставить пломбу?» → ответ из прайса
2. «Когда работает ортодонт?» → ответ из расписания
3. «Как подготовиться к приёму?» → ответ из FAQ
4. «Вы делаете МРТ?» → «У меня нет информации, оставьте номер»
5. «How much is teeth cleaning?» → ответ на английском из прайса

---

# 10. КЛЮЧЕВЫЕ МЕТРИКИ УСПЕХА MVP

- Латентность: < 2 секунды от конца речи клиента до начала ответа аватара
- Точность STT на русском: > 95%
- Аватар не выдумывает: 0 случаев галлюцинации на 50 тестовых вопросах
- Стабильность: 30-минутный диалог без разрывов
- Мобильный браузер: работает на Safari iOS и Chrome Android
