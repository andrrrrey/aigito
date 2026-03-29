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
                              │   GPT-4o-mini + ElevenLabs     │
                              │   STT (Scribe v2, русский)     │
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
| STT | ElevenLabs Scribe v2 (русский язык) |
| LLM | OpenAI GPT-4o-mini |
| TTS | ElevenLabs eleven_flash_v2_5 |
| RAG | OpenAI text-embedding-3-small → Qdrant |
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
├── livekit.yaml              # LiveKit dev конфиг
├── livekit.prod.yaml         # LiveKit prod конфиг
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
nano .env  # заполните API ключи
```

### 3. Запуск

```bash
docker compose up -d --build
```

### 4. Демо данные

```bash
docker compose exec backend python /scripts/seed_demo.py
```

### 5. Доступ

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
# База данных
POSTGRES_USER=aigita
POSTGRES_PASSWORD=<ПРИДУМАЙТЕ_НАДЁЖНЫЙ_ПАРОЛЬ>

# LiveKit — ключ и секрет должны совпадать с livekit.prod.yaml
LIVEKIT_API_KEY=aigita_prod_key
LIVEKIT_API_SECRET=<см. команду ниже>
LIVEKIT_URL=wss://app.aigito.com/rtc

# OpenAI
OPENAI_API_KEY=sk-proj-...

# ElevenLabs
ELEVENLABS_API_KEY=sk_...

# Lemon Slice (опционально, для видео-аватара)
LEMONSLICE_API_KEY=

# JWT
JWT_SECRET=<см. команду ниже>
ENVIRONMENT=production
```

Сгенерировать секреты:

```bash
echo "LIVEKIT_API_SECRET=$(openssl rand -hex 32)"
echo "JWT_SECRET=$(openssl rand -hex 32)"
```

#### 6.2 LiveKit production конфиг

```bash
nano livekit.prod.yaml
```

```yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
keys:
  aigita_prod_key: <ТОТ_ЖЕ_LIVEKIT_API_SECRET_ЧТО_В_.ENV>
logging:
  level: warn
```

> **Важно:** значение после `aigita_prod_key:` должно **точно совпадать** с `LIVEKIT_API_SECRET` в `.env`.

#### 6.3 Nginx production конфиг

Заменить заглушку `YOUR_DOMAIN` на реальный домен:

```bash
sed -i 's/YOUR_DOMAIN/app.aigito.com/g' nginx/nginx.prod.conf

# Проверить
grep server_name nginx/nginx.prod.conf
# server_name app.aigito.com www.app.aigito.com;
```

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
# Миграции запускаются автоматически при старте backend.
# Для ручного запуска:
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec backend alembic upgrade head

# Загрузить демо данные стоматологии (опционально)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec backend python /scripts/seed_demo.py
```

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
  exec backend python /scripts/test_pipeline.py
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

| Переменная | Описание | Получить |
|------------|----------|---------|
| `POSTGRES_USER` | Пользователь PostgreSQL | придумать |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | придумать |
| `LIVEKIT_API_KEY` | LiveKit API ключ (имя) | придумать |
| `LIVEKIT_API_SECRET` | LiveKit API секрет | `openssl rand -hex 32` |
| `LIVEKIT_URL` | LiveKit URL для клиентов | `wss://app.aigito.com/rtc` |
| `OPENAI_API_KEY` | OpenAI API ключ | platform.openai.com |
| `ELEVENLABS_API_KEY` | ElevenLabs API ключ | elevenlabs.io |
| `LEMONSLICE_API_KEY` | Lemon Slice (опционально) | lemonslice.com |
| `JWT_SECRET` | Секрет для JWT токенов | `openssl rand -hex 32` |
| `ENVIRONMENT` | Окружение | `production` |

---

## Известные ограничения

- **Lemon Slice** (реалистичный видео-аватар) — подключается опционально. Без ключа платформа работает в голосовом режиме.
- **UDP-порты 50000–60000** обязательны для WebRTC. В строгих NAT-средах рекомендуется включить TURN в `livekit.prod.yaml`: добавьте блок `turn: { enabled: true }`.
- **minutes_used** — счётчик минут в таблице `companies` обновляется автоматически агентом по завершении каждого диалога.

---

## Лицензия

MIT
