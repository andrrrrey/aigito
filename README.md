# AIGITO — AI Video Avatar для офлайн-бизнеса

AIGITO — платформа голосового AI-аватара для развёртывания на киосках, планшетах и телевизорах в офлайн-точках бизнеса (кафе, стоматологии, салоны, магазины). Аватар отвечает на вопросы клиентов в реальном времени, используя базу знаний конкретной компании.

---

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                     NGINX (SSL/TLS)                          │
│             app.aigito.com → 80 / 443                        │
└────────┬─────────────┬──────────────┬────────────────────────┘
         │             │              │
    /admin/        /kiosk/         /api/           /rtc (WS)
         │             │              │                 │
   ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐  ┌───────▼──────┐
   │   Admin   │ │   Kiosk   │ │  FastAPI  │  │   LiveKit    │
   │   Panel   │ │ Frontend  │ │  Backend  │  │   Server     │
   └───────────┘ └───────────┘ └─────┬─────┘  └───────┬──────┘
                                     │                 │
                              ┌──────▼─────────────────▼──────┐
                              │         LiveKit Agent          │
                              │   GPT-4o-mini + OpenAI TTS     │
                              │   STT (Deepgram Nova-3, рус.)  │
                              │   RAG pipeline (Qdrant)        │
                              └──────┬──────────────┬──────────┘
                                     │              │
                               ┌─────▼────┐  ┌─────▼────┐
                               │PostgreSQL│  │  Qdrant  │
                               └──────────┘  └──────────┘
                                     │
                               ┌─────▼────┐
                               │  Redis   │
                               └──────────┘
```

### Стек технологий

| Компонент | Технология |
|-----------|------------|
| Backend API | Python 3.11, FastAPI, SQLAlchemy 2.0 async |
| AI Agent | LiveKit Agents SDK 1.5.1 |
| STT | Deepgram Nova-3 (русский язык) |
| LLM | OpenAI GPT-4o-mini |
| TTS | OpenAI TTS-1 (голоса: alloy, echo, fable, onyx, nova, shimmer) |
| RAG | OpenAI text-embedding-3-small → Qdrant |
| Видео-аватар | Lemon Slice (опционально) |
| База данных | PostgreSQL 16 + Alembic |
| Кэш | Redis 7 |
| WebRTC | LiveKit (self-hosted) |
| Фронтенд | Vanilla JS + HTML |
| Прокси | Nginx + Let's Encrypt |
| Инфраструктура | Docker Compose |

---

## Структура проекта

```
aigito/
├── backend/                  # FastAPI приложение
│   ├── auth/                 # JWT аутентификация
│   ├── companies/            # Управление компаниями
│   ├── knowledge/            # База знаний + RAG ingestion
│   ├── analytics/            # Аналитика диалогов
│   ├── kiosk/                # Генерация LiveKit токенов
│   ├── alembic/              # Миграции БД
│   ├── requirements.txt
│   ├── Dockerfile
│   └── start.sh              # alembic upgrade head + uvicorn
│
├── agent/                    # LiveKit AI агент
│   ├── aigita_agent.py       # Основная логика агента
│   ├── rag.py                # Семантический поиск (Qdrant)
│   ├── dialog_tracker.py     # Запись диалогов в PostgreSQL
│   ├── prompt_builder.py     # Построение системного промпта
│   ├── llm_router.py         # Выбор LLM модели
│   ├── config.py             # Настройки из окружения
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend-kiosk/           # Интерфейс киоска
│   ├── index.html
│   ├── app.js                # Логика + автопереподключение
│   ├── livekit-client.js     # Обёртка LiveKit SDK
│   ├── style.css
│   └── ui.js
│
├── frontend-admin/           # Административная панель
│   └── pages/
│       ├── dashboard.html    # График диалогов + статистика
│       ├── knowledge.html    # Управление базой знаний
│       ├── settings.html     # Настройки компании
│       └── avatar.html       # Предпросмотр аватара
│
├── nginx/
│   ├── nginx.conf            # Dev конфиг
│   ├── nginx.prod.conf       # Prod конфиг с SSL
│   └── Dockerfile
│
├── scripts/
│   ├── seed_demo.py          # Демо данные (стоматология)
│   ├── test_pipeline.py      # Интеграционные тесты
│   └── deploy.sh             # Скрипт деплоя
│
├── docker-compose.yml        # Dev окружение
├── docker-compose.prod.yml   # Prod оверрайды
├── livekit.yaml.example      # LiveKit dev конфиг (скопировать → livekit.yaml)
├── livekit.prod.yaml.example # LiveKit prod конфиг (скопировать → livekit.prod.yaml)
└── .env.example              # Шаблон переменных окружения
```

---

## API эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/api/auth/register` | Регистрация |
| `POST` | `/api/auth/login` | Вход, получение JWT |
| `GET` | `/api/companies/me` | Данные своей компании |
| `PUT` | `/api/companies/me` | Обновление компании |
| `GET` | `/api/knowledge/documents` | Список документов |
| `POST` | `/api/knowledge/documents` | Загрузить документ (PDF/DOCX/TXT/CSV) |
| `DELETE` | `/api/knowledge/documents/{id}` | Удалить документ |
| `POST` | `/api/knowledge/rebuild` | Перестроить индекс Qdrant |
| `GET` | `/api/analytics/stats` | Сводная статистика |
| `GET` | `/api/analytics/dialogs` | Список диалогов с фильтрами |
| `GET` | `/api/analytics/dialogs/{id}/messages` | Сообщения диалога |
| `GET` | `/api/analytics/dialogs-chart?days=30` | Данные для Chart.js |
| `POST` | `/api/kiosk/token` | LiveKit токен для киоска |
| `GET` | `/health` | Healthcheck |

Swagger UI: `https://app.aigito.com/api/docs`

---

## Необходимые API ключи

Перед установкой получите ключи:

| Ключ | Обязательный | Для чего | Где получить |
|------|:------------:|----------|-------------|
| `OPENAI_API_KEY` | **Да** | LLM (GPT-4o-mini), TTS (tts-1), RAG-эмбеддинги | [platform.openai.com](https://platform.openai.com) |
| `DEEPGRAM_API_KEY` | **Да** | STT — распознавание речи (Nova-3, русский) | [deepgram.com](https://deepgram.com) |
| `ELEVENLABS_API_KEY` | Нет | Альтернативный TTS (не используется по умолчанию) | [elevenlabs.io](https://elevenlabs.io) |
| `LEMONSLICE_API_KEY` | Нет | Видео-аватар. Без ключа — голосовой режим | [lemonslice.com](https://lemonslice.com) |

---

## Быстрый старт (локальная разработка)

### Требования

- Docker + Docker Compose V2 (`docker compose version`)
- Git

### 1. Клонирование

```bash
git clone https://github.com/andrrrrey/aigito.git
cd aigito
```

### 2. Переменные окружения

```bash
cp .env.example .env
nano .env  # заполните API ключи (минимум OPENAI_API_KEY и DEEPGRAM_API_KEY)
```

### 3. Конфигурация LiveKit

```bash
cp livekit.yaml.example livekit.yaml
```

Отредактируйте `livekit.yaml` — ключи должны совпадать со значениями в `.env`:

```yaml
keys:
  aigita_dev_key: aigita_dev_secret_change_me  # LIVEKIT_API_KEY: LIVEKIT_API_SECRET
```

> По умолчанию `.env.example` содержит `LIVEKIT_API_KEY=aigita_dev_key` и `LIVEKIT_API_SECRET=aigita_dev_secret_change_me`. Если вы их изменили в `.env`, обновите и в `livekit.yaml`.

### 4. Запуск

```bash
docker compose up -d --build
```

### 5. Демо данные (опционально)

```bash
docker compose run --rm \
  -v ./scripts:/opt/scripts \
  -e PYTHONPATH=/app \
  backend python /opt/scripts/seed_demo.py
```

### 6. Доступ

| Сервис | URL | Логин |
|--------|-----|-------|
| Админ-панель | http://localhost/admin/ | demo@aigito.ru / demo123 |
| Киоск | http://localhost/kiosk/ | — |
| API Docs | http://localhost/api/docs | — |

---

## Деплой на VPS с доменом app.aigito.com

### Требования к серверу

- VPS: **2 CPU, 4 GB RAM, 40 GB SSD** (минимум)
- ОС: Ubuntu 22.04 LTS или Debian 12
- Открытые порты: `80`, `443`, `7880`, `7881`, `50000–60000/UDP`
- DNS: A-запись `app.aigito.com` → IP сервера уже добавлена и распространилась

---

### Шаг 1 — Подготовка сервера

```bash
# Подключиться к VPS
ssh root@<IP_СЕРВЕРА>

# Обновить систему
apt update && apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Проверить Docker Compose V2
docker compose version
# Docker Compose version v2.x.x

# Если plugin не установлен:
apt install -y docker-compose-plugin

# Установить certbot
apt install -y certbot

# Создать директорию проекта
mkdir -p /opt/aigito
```

---

### Шаг 2 — DNS настройка

В панели управления доменом добавьте A-запись:

```
app.aigito.com  →  <IP_ВАШЕГО_VPS>
```

Дождитесь распространения (обычно 5–30 минут) и проверьте:

```bash
nslookup app.aigito.com
# Address: <IP_ВАШЕГО_VPS>
```

---

### Шаг 3 — Открыть порты в файрволе

```bash
ufw allow 22/tcp           # SSH (обязательно не забыть!)
ufw allow 80/tcp           # HTTP
ufw allow 443/tcp          # HTTPS
ufw allow 7880/tcp         # LiveKit HTTP/WS
ufw allow 7881/tcp         # LiveKit RTC TCP
ufw allow 50000:60000/udp  # LiveKit WebRTC media
ufw allow 5349/tcp         # LiveKit TURN TLS
ufw allow 3478/udp         # LiveKit TURN UDP
ufw enable
ufw status
```

Если VPS в облаке (Hetzner, DigitalOcean, Timeweb Cloud) — добавьте те же правила в веб-интерфейсе облачного файрвола.

---

### Шаг 4 — Клонирование кода

```bash
cd /opt/aigito
git clone https://github.com/andrrrrey/aigito.git .
```

---

### Шаг 5 — Получение SSL-сертификата

> Перед этим шагом убедитесь, что порт 80 свободен (nginx ещё не запущен).

```bash
certbot certonly --standalone \
  -d app.aigito.com \
  --email admin@aigito.com \
  --agree-tos \
  --no-eff-email

# Сертификаты окажутся в:
# /etc/letsencrypt/live/app.aigito.com/fullchain.pem
# /etc/letsencrypt/live/app.aigito.com/privkey.pem

# Проверить
ls /etc/letsencrypt/live/app.aigito.com/
```

Настройка автообновления сертификата:

```bash
# Обновлять сертификат 1-го и 15-го числа каждого месяца в 3:00
(crontab -l 2>/dev/null; echo "0 3 1,15 * * certbot renew --quiet && docker compose -f /opt/aigito/docker-compose.yml -f /opt/aigito/docker-compose.prod.yml restart nginx") | crontab -
```

---

### Шаг 6 — Настройка конфигурации

#### 6.1 Переменные окружения

```bash
cd /opt/aigito
cp .env.example .env
nano .env
```

Содержимое `.env` для production:

```env
# === База данных ===
POSTGRES_USER=aigita
POSTGRES_PASSWORD=<ПРИДУМАЙТЕ_НАДЁЖНЫЙ_ПАРОЛЬ>

# === LiveKit ===
# Ключ и секрет ДОЛЖНЫ совпадать с livekit.prod.yaml
LIVEKIT_API_KEY=aigita_prod_key
LIVEKIT_API_SECRET=<см. команду ниже>
# LIVEKIT_URL переопределяется в docker-compose — указывать не нужно
# Публичный URL для Lemon Slice видео-аватара (опционально):
LIVEKIT_PUBLIC_URL=wss://app.aigito.com/rtc

# === AI сервисы (обязательные) ===
OPENAI_API_KEY=sk-proj-...
DEEPGRAM_API_KEY=...

# === AI сервисы (опциональные) ===
ELEVENLABS_API_KEY=
LEMONSLICE_API_KEY=

# === Приложение ===
JWT_SECRET=<см. команду ниже>
ENVIRONMENT=production
```

Сгенерировать секреты:

```bash
echo "LIVEKIT_API_SECRET=$(openssl rand -hex 32)"
echo "JWT_SECRET=$(openssl rand -hex 32)"
```

> Скопируйте сгенерированные значения в `.env`. Значение `LIVEKIT_API_SECRET` также понадобится на следующем шаге для `livekit.prod.yaml`.

#### 6.2 LiveKit production конфиг

```bash
cp livekit.prod.yaml.example livekit.prod.yaml
nano livekit.prod.yaml
```

Замените плейсхолдеры на реальные значения:

```yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
  node_ip: <IP_ВАШЕГО_VPS>          # ← заменить на реальный IP сервера
  allow_tcp_fallback: true
  pli_throttle:
    low_quality: 500ms
    mid_quality: 1s
    high_quality: 1s
keys:
  aigita_prod_key: <LIVEKIT_API_SECRET_ИЗ_.ENV>   # ← заменить
logging:
  level: info
turn:
  enabled: true
  domain: <ВАШ_ДОМЕН>              # ← заменить (например app.aigito.com)
  cert_file: /etc/letsencrypt/live/<ВАШ_ДОМЕН>/fullchain.pem   # ← заменить
  key_file: /etc/letsencrypt/live/<ВАШ_ДОМЕН>/privkey.pem      # ← заменить
  tls_port: 5349
  udp_port: 3478
```

> **Важно:**
> - Значение после `aigita_prod_key:` должно **точно совпадать** с `LIVEKIT_API_SECRET` в `.env`
> - `node_ip` — внешний IP вашего VPS (не 127.0.0.1)
> - `turn.domain` — ваш домен для TURN-сервера (нужен для клиентов за строгим NAT)

#### 6.3 Nginx production конфиг

Nginx-конфиг по умолчанию настроен на домен `app.aigito.com`. Если у вас **другой домен**, замените:

```bash
# Заменить домен (только если НЕ app.aigito.com)
sed -i 's/app.aigito.com/ваш-домен.com/g' nginx/nginx.prod.conf

# Проверить
grep server_name nginx/nginx.prod.conf
```

Также обновите пути к SSL-сертификатам, если домен другой:

```bash
grep ssl_certificate nginx/nginx.prod.conf
# Должно соответствовать путям из шага 5 (certbot)
```

> Если ваш домен `app.aigito.com` — этот шаг можно пропустить, конфиг уже готов.

---

### Шаг 7 — Первый запуск

```bash
cd /opt/aigito

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Следить за запуском:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

> **Особенности production-сети:** В продакшен-конфигурации `agent` и `livekit` работают с `network_mode: host` — они используют сетевой стек хоста напрямую. Поэтому агент подключается к сервисам через `localhost` (PostgreSQL, Qdrant, LiveKit), а не через Docker DNS.

Ожидаемое состояние через ~60 секунд:

```
NAME              STATUS    PORTS
aigito-postgres   healthy   5432/tcp
aigito-qdrant     healthy   6333/tcp
aigito-redis      healthy   6379/tcp
aigito-livekit    healthy   7880/tcp, 7881/tcp
aigito-backend    running   8000/tcp
aigito-agent      running
aigito-nginx      running   0.0.0.0:80->80, 0.0.0.0:443->443
```

---

### Шаг 8 — Миграции и демо данные

```bash
# Миграции запускаются автоматически при старте backend (start.sh → alembic upgrade head).
# Для ручного запуска:
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec backend alembic upgrade head

# Загрузить демо данные стоматологии (опционально)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm -v ./scripts:/opt/scripts -e PYTHONPATH=/app \
  backend python /opt/scripts/seed_demo.py
```

> Скрипты из `scripts/` не включены в Docker-образ backend, поэтому монтируются отдельно через `-v`.

---

### Шаг 9 — Проверка работоспособности

```bash
# Backend health
curl -f https://app.aigito.com/api/health
# {"status":"ok","service":"aigito-backend"}

# Qdrant
curl http://localhost:6333/healthz

# Полный интеграционный тест всех сервисов
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm -v ./scripts:/opt/scripts -e PYTHONPATH=/app \
  backend python /opt/scripts/test_pipeline.py
```

Откройте в браузере:

| URL | Что открывается |
|-----|-----------------|
| `https://app.aigito.com/admin/` | Административная панель |
| `https://app.aigito.com/kiosk/` | Интерфейс киоска |
| `https://app.aigito.com/api/docs` | Swagger UI |

---

### Шаг 10 — Автозапуск при перезагрузке

```bash
cat > /etc/systemd/system/aigito.service << 'EOF'
[Unit]
Description=AIGITO Platform
Requires=docker.service
After=docker.service network-online.target

[Service]
WorkingDirectory=/opt/aigito
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up
ExecStop=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aigito
```

---

## Обновление кода (последующие деплои)

```bash
cd /opt/aigito
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Скрипт выполнит:
1. `git pull` — загрузит новый код
2. `docker compose build` — пересоберёт образы
3. Поднимет БД, дождётся готовности
4. Запустит `alembic upgrade head`
5. Поднимет все сервисы
6. Выполнит healthcheck

---

## Управление сервисами

```bash
# Удобный псевдоним (добавьте в ~/.bashrc)
alias dc='docker compose -f /opt/aigito/docker-compose.yml -f /opt/aigito/docker-compose.prod.yml'

# Логи
dc logs -f backend
dc logs -f agent
dc logs -f nginx

# Перезапуск отдельного сервиса
dc restart backend
dc restart agent

# Остановить всё
dc down

# Запустить всё
dc up -d
```

---

## Мониторинг и отладка

### Просмотр диалогов в БД

```bash
docker compose exec postgres psql -U aigita -d aigita

-- Последние диалоги
SELECT started_at, duration_seconds, message_count
FROM dialogs ORDER BY started_at DESC LIMIT 10;

-- Использование минут по компаниям
SELECT name, minutes_used FROM companies;

-- Количество документов в базе знаний
SELECT c.name, COUNT(k.id) AS docs
FROM companies c LEFT JOIN knowledge_documents k ON k.company_id = c.id
GROUP BY c.name;
```

### Просмотр векторной БД Qdrant

```bash
# Список коллекций
curl http://localhost:6333/collections

# Статистика коллекции конкретной компании (подставьте UUID)
curl http://localhost:6333/collections/company_<UUID>
```

### Перестройка индекса знаний

Если документы загружены, но RAG не отвечает:

```bash
curl -X POST https://app.aigito.com/api/knowledge/rebuild \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

---

## Устранение неполадок

### Агент не подключается к LiveKit

```bash
# Проверить что LiveKit запущен
curl http://localhost:7880/
# Проверить логи агента
dc logs agent --tail=50
```

В продакшене агент работает с `network_mode: host` и подключается к `ws://localhost:7880`. Убедитесь что LiveKit слушает на порту 7880.

### Нет звука / видео на киоске

1. Проверьте что UDP-порты `50000–60000` открыты на файрволе VPS и в облачном файрволе
2. Проверьте `node_ip` в `livekit.prod.yaml` — должен быть внешний IP сервера
3. Если клиент за строгим NAT — убедитесь что TURN включён в `livekit.prod.yaml`
4. Проверьте логи LiveKit: `dc logs livekit --tail=50`

### STT не распознаёт речь

```bash
# Проверить что DEEPGRAM_API_KEY установлен
dc exec agent env | grep DEEPGRAM
```

Если переменная пуста — добавьте валидный ключ Deepgram в `.env` и перезапустите: `dc restart agent`.

### Ключи LiveKit не совпадают

Ошибка `could not verify token` в логах — означает несовпадение ключей.

Проверьте:
1. `LIVEKIT_API_KEY` в `.env` совпадает с именем ключа в `livekit.prod.yaml` (`keys:` секция)
2. `LIVEKIT_API_SECRET` в `.env` совпадает со значением этого ключа в `livekit.prod.yaml`

```bash
# Проверить значения
grep LIVEKIT_API .env
grep keys -A1 livekit.prod.yaml
```

### База знаний не работает (RAG не отвечает)

```bash
# Проверить Qdrant
curl http://localhost:6333/collections
# Перестроить индекс (нужен JWT-токен)
curl -X POST https://app.aigito.com/api/knowledge/rebuild \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### SSL-сертификат не обновился

```bash
# Ручное обновление
certbot renew
# Перезапустить nginx
dc restart nginx
```

Убедитесь что порт 80 доступен извне для ACME-проверки.

### Контейнер backend не запускается

```bash
dc logs backend --tail=100
```

Частые причины:
- PostgreSQL ещё не готов (обычно решается само через health checks)
- Ошибка миграции: `dc exec backend alembic upgrade head`
- Неверный `DATABASE_URL` (проверьте `POSTGRES_USER` и `POSTGRES_PASSWORD` в `.env`)

---

## Первичная настройка компании

После деплоя:

1. Откройте **https://app.aigito.com/admin/**
2. Нажмите «Регистрация» → создайте учётную запись компании
3. **Настройки** → заполните:
   - Название компании
   - Описание локации (используется агентом как контекст)
   - Дополнительные правила поведения аватара
   - Voice ID из ElevenLabs (если нужен кастомный голос)
4. **База знаний** → загрузите документы (PDF, DOCX, TXT, CSV)
   - Загрузка асинхронная: файл принимается мгновенно, векторизация идёт в фоне
5. Откройте **https://app.aigito.com/kiosk/** на планшете — аватар готов

---

## Справочник переменных окружения

| Переменная | Описание | Обязательная | Получить |
|------------|----------|:------------:|---------|
| `POSTGRES_USER` | Пользователь PostgreSQL | Да | придумать |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | Да | придумать |
| `LIVEKIT_API_KEY` | LiveKit API ключ (имя) | Да | придумать (должен совпадать с `livekit.yaml`) |
| `LIVEKIT_API_SECRET` | LiveKit API секрет | Да | `openssl rand -hex 32` |
| `LIVEKIT_PUBLIC_URL` | Публичный WSS URL для Lemon Slice | Нет | `wss://ваш-домен.com/rtc` |
| `OPENAI_API_KEY` | OpenAI (LLM, TTS, эмбеддинги) | Да | [platform.openai.com](https://platform.openai.com) |
| `DEEPGRAM_API_KEY` | Deepgram (STT, распознавание речи) | Да | [deepgram.com](https://deepgram.com) |
| `ELEVENLABS_API_KEY` | ElevenLabs (альтернативный TTS) | Нет | [elevenlabs.io](https://elevenlabs.io) |
| `LEMONSLICE_API_KEY` | Lemon Slice (видео-аватар) | Нет | [lemonslice.com](https://lemonslice.com) |
| `JWT_SECRET` | Секрет для JWT токенов | Да | `openssl rand -hex 32` |
| `ENVIRONMENT` | Окружение (`development` / `production`) | Да | `production` для VPS |

> Переменные `DATABASE_URL`, `REDIS_URL`, `QDRANT_HOST`, `QDRANT_PORT`, `LIVEKIT_URL` задаются автоматически в `docker-compose.yml` и не требуют указания в `.env`.

---

## Известные ограничения

- **Lemon Slice** (реалистичный видео-аватар) — подключается опционально. Без ключа платформа работает в голосовом режиме.
- **UDP-порты 50000–60000** обязательны для WebRTC. В строгих NAT-средах рекомендуется включить TURN в `livekit.prod.yaml`: добавьте блок `turn: { enabled: true }`.
- **minutes_used** — счётчик минут в таблице `companies` обновляется автоматически агентом по завершении каждого диалога.

---

## Лицензия

MIT
