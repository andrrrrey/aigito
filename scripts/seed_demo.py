"""
Seed demo data: «Стоматология Улыбка»
  1. Creates demo User + Company + KnowledgeDocument in PostgreSQL
  2. Embeds demo knowledge into Qdrant

Usage (run inside docker-compose network or locally with DB accessible):
  python scripts/seed_demo.py
"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from auth.models import User
from auth.jwt import hash_password
from companies.models import Company
from knowledge.models import KnowledgeDocument

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aigita:aigita_dev_password@localhost:5432/aigita",
)

DEMO_KNOWLEDGE = """
ПРАЙС-ЛИСТ СТОМАТОЛОГИИ УЛЫБКА:
- Консультация стоматолога: 1500 руб.
- Профессиональная чистка зубов (Air Flow): 4500 руб.
- Пломба световая (1 поверхность): 3500 руб., (2 поверхности): 4500 руб.
- Виниры керамические: от 25000 руб. за зуб
- Брекет-система металлическая: от 80000 руб.
- Брекет-система керамическая: от 120000 руб.
- Отбеливание зубов (системой ZOOM): 12000 руб.
- Удаление зуба простое: 2500 руб.
- Удаление зуба сложное: 5000 руб.
- Имплант (под ключ): от 55000 руб.

ВРАЧИ И РАСПИСАНИЕ:
- Иванова Анна Сергеевна (терапевт, стаж 12 лет): пн-пт 9:00-18:00
- Петров Константин Михайлович (ортодонт, к.м.н.): вт, чт 10:00-19:00
- Смирнова Елена Викторовна (хирург-имплантолог): пн, ср, пт 9:00-17:00
- Козлова Марина Дмитриевна (детский стоматолог): пн-пт 9:00-16:00

КАК ПОДГОТОВИТЬСЯ К ПРИЁМУ:
- Не есть за 2 часа до визита
- Взять с собой паспорт и полис ОМС
- По возможности принести результаты предыдущих рентгенов
- Для первичного приёма заложите 30-60 минут

АДРЕС И ВРЕМЯ РАБОТЫ:
- Адрес: ул. Ленина 42, 2 этаж, вход со двора (кодовый замок 1234#)
- Ближайшее метро: Площадь Ленина (5 мин пешком)
- Пн-Пт: 9:00-20:00
- Суббота: 10:00-16:00
- Воскресенье: выходной
- Телефон для записи: +7 (495) 123-45-67
- WhatsApp: +7 (495) 123-45-67

ЗАПИСЬ НА ПРИЁМ:
Записаться можно по телефону +7 (495) 123-45-67, через WhatsApp,
или оставьте свой номер — мы перезвоним в течение 15 минут.

ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ:
- Принимаете ли по ОМС? Да, принимаем по ОМС на терапевтическое лечение.
- Есть ли рассрочка? Да, рассрочка 0% на 12 месяцев через банк-партнёр.
- Делаете ли МРТ? Нет, МРТ мы не делаем, только дентальный рентген.
- Работаете ли в праздники? В государственные праздники — выходной.
"""


async def seed_postgres():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # User
        result = await db.execute(select(User).where(User.email == "demo@aigito.ru"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="demo@aigito.ru",
                hashed_password=hash_password("demo123"),
                full_name="Demo Owner",
            )
            db.add(user)
            await db.flush()
            logger.info("Created demo user: demo@aigito.ru / demo123")
        else:
            logger.info(f"User exists: {user.email}")

        # Company
        result = await db.execute(select(Company).where(Company.slug == "dental-smile"))
        company = result.scalar_one_or_none()
        if not company:
            company = Company(
                name="Стоматология Улыбка",
                slug="dental-smile",
                location_description="зона ожидания стоматологии",
                custom_rules="Всегда предлагай записаться на приём. Будь приветливым и внимательным.",
                plan="starter",
                minutes_limit=300,
                owner_id=user.id,
            )
            db.add(company)
            await db.flush()
            logger.info(f"Created demo company: dental-smile (id={company.id})")
        else:
            logger.info(f"Company exists: {company.slug} (id={company.id})")

        # KnowledgeDocument
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.company_id == company.id,
                KnowledgeDocument.filename == "demo_knowledge.txt",
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            doc = KnowledgeDocument(
                company_id=company.id,
                filename="demo_knowledge.txt",
                file_type="txt",
                content_text=DEMO_KNOWLEDGE,
                chunks_count=0,
            )
            db.add(doc)
            await db.flush()
            logger.info("Created demo knowledge document")

        await db.commit()
        company_id = str(company.id)
        doc_id = str(doc.id)

    await engine.dispose()
    return company_id, doc_id


async def seed_qdrant(company_id: str, doc_id: str):
    """Embed demo knowledge and upsert into Qdrant."""
    try:
        # Import from backend
        from knowledge.ingest import ingest_document, chunk_text

        logger.info(f"Seeding Qdrant for company {company_id}...")
        chunks = await ingest_document(company_id, doc_id, DEMO_KNOWLEDGE)
        logger.info(f"Seeded {chunks} chunks into Qdrant collection company_{company_id}")
    except Exception as e:
        logger.warning(f"Qdrant seeding failed (non-critical for Stage 1): {e}")
        logger.warning("Run this script again once Qdrant + OpenAI keys are configured.")


async def main():
    logger.info("=" * 50)
    logger.info("AIGITO Demo Seed")
    logger.info("=" * 50)

    company_id, doc_id = await seed_postgres()
    await seed_qdrant(company_id, doc_id)

    logger.info("")
    logger.info("Demo data ready!")
    logger.info("  Admin login:   demo@aigito.ru / demo123")
    logger.info("  Kiosk URL:     http://localhost/kiosk/dental-smile")
    logger.info("  Admin URL:     http://localhost/admin/")


asyncio.run(main())
