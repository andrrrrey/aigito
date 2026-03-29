"""
Seed demo data: «Стоматология Улыбка»
Usage: python scripts/seed_demo.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from auth.models import User
from auth.jwt import hash_password
from companies.models import Company
from knowledge.models import KnowledgeDocument
from database import Base

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://aigita:aigita_dev_password@localhost:5432/aigita')

DEMO_KNOWLEDGE = """
ПРАЙС-ЛИСТ:
- Консультация стоматолога: 1500 руб.
- Профессиональная чистка зубов: 4500 руб.
- Пломба световая: от 3500 руб.
- Виниры: от 25000 руб. за зуб
- Брекет-система: от 80000 руб.
- Отбеливание зубов: 12000 руб.

ВРАЧИ:
- Иванова Анна Сергеевна (терапевт): пн-пт 9:00-18:00
- Петров Константин Михайлович (ортодонт): вт-чт 10:00-19:00
- Смирнова Елена Викторовна (хирург): пн,ср,пт 9:00-17:00

ПОДГОТОВКА К ПРИЁМУ:
- Не есть за 2 часа до визита
- Взять с собой паспорт и полис ОМС
- По возможности — результаты предыдущих анализов

АДРЕС И ВРЕМЯ РАБОТЫ:
- Адрес: ул. Ленина 42, 2 этаж, вход со двора
- Пн-Пт: 9:00-20:00
- Сб: 10:00-16:00
- Вс: выходной
- Телефон: +7 (495) 123-45-67

ЗАПИСЬ НА ПРИЁМ:
Записаться можно по телефону +7 (495) 123-45-67 или оставить контакт — перезвоним.
"""

async def main():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Create demo user
        result = await db.execute(select(User).where(User.email == 'demo@aigito.ru'))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email='demo@aigito.ru',
                hashed_password=hash_password('demo123'),
                full_name='Demo Owner',
            )
            db.add(user)
            await db.flush()
            print(f"Created demo user: demo@aigito.ru / demo123")
        else:
            print(f"Demo user already exists: {user.email}")

        # Create demo company
        result = await db.execute(select(Company).where(Company.slug == 'dental-smile'))
        company = result.scalar_one_or_none()
        if not company:
            company = Company(
                name='Стоматология Улыбка',
                slug='dental-smile',
                location_description='зона ожидания стоматологии',
                custom_rules='Всегда предлагай записаться на приём. Будь доброжелательным.',
                plan='starter',
                minutes_limit=300,
                owner_id=user.id,
            )
            db.add(company)
            await db.flush()
            print(f"Created demo company: dental-smile")
        else:
            print(f"Demo company already exists: {company.slug}")

        # Create demo knowledge document
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.company_id == company.id,
                KnowledgeDocument.filename == 'demo_knowledge.txt',
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            doc = KnowledgeDocument(
                company_id=company.id,
                filename='demo_knowledge.txt',
                file_type='txt',
                content_text=DEMO_KNOWLEDGE,
                chunks_count=0,
            )
            db.add(doc)
            await db.flush()
            print(f"Created demo knowledge document")

        await db.commit()
        print("\nDemo data seeded successfully!")
        print("  Kiosk URL: http://localhost/kiosk/dental-smile")
        print("  Admin login: demo@aigito.ru / demo123")

    await engine.dispose()

asyncio.run(main())
