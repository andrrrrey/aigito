"""
Saves dialog sessions and messages to PostgreSQL directly via asyncpg.
Called from the agent at session start/end and on each message.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from config import settings
from memory_learning import learn_from_dialog

logger = logging.getLogger(__name__)


class DialogTracker:
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.dialog_id: Optional[str] = str(uuid.uuid4())
        self.started_at: datetime = datetime.now(timezone.utc)
        self._conn: Optional[asyncpg.Connection] = None
        self._messages: list[dict] = []

    async def _get_conn(self) -> asyncpg.Connection:
        if self._conn is None or self._conn.is_closed():
            db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            self._conn = await asyncpg.connect(db_url)
        return self._conn

    async def start(self):
        """Insert a new dialog row."""
        try:
            conn = await self._get_conn()
            await conn.execute(
                """
                INSERT INTO dialogs (id, company_id, started_at, language)
                VALUES ($1::uuid, $2::uuid, $3, 'ru')
                """,
                self.dialog_id,
                self.company_id,
                self.started_at,
            )
            logger.info(f"Dialog started: {self.dialog_id}")
        except Exception as e:
            logger.warning(f"Failed to start dialog tracking: {e}")

    async def add_message(self, role: str, content: str):
        """Insert a dialog message."""
        self._messages.append({"role": role, "content": content})
        try:
            conn = await self._get_conn()
            await conn.execute(
                """
                INSERT INTO dialog_messages (id, dialog_id, role, content, timestamp)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5)
                """,
                str(uuid.uuid4()),
                self.dialog_id,
                role,
                content,
                datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"Failed to save message: {e}")

    async def _get_memory_enabled(self) -> bool:
        """Read avatar_memory_enabled flag for this company."""
        try:
            conn = await self._get_conn()
            row = await conn.fetchrow(
                "SELECT avatar_memory_enabled FROM companies WHERE id = $1::uuid",
                self.company_id,
            )
            if row is None:
                return False
            return bool(row["avatar_memory_enabled"])
        except Exception as e:
            logger.warning("Failed to read avatar_memory_enabled: %s", e)
            return False

    async def finish(self, duration_seconds: Optional[float] = None):
        """Update dialog with end time and duration."""
        ended_at = datetime.now(timezone.utc)
        if duration_seconds is None:
            duration_seconds = (ended_at - self.started_at).total_seconds()

        # Auto-extract topics from messages (simple keyword matching)
        topics = self._extract_topics()

        memory_enabled = False
        try:
            conn = await self._get_conn()
            await conn.execute(
                """
                UPDATE dialogs
                SET ended_at = $1, duration_seconds = $2, topics = $3::jsonb
                WHERE id = $4::uuid
                """,
                ended_at,
                duration_seconds,
                json.dumps(topics, ensure_ascii=False),
                self.dialog_id,
            )
            # Update minutes_used on company
            minutes = duration_seconds / 60.0
            await conn.execute(
                """
                UPDATE companies
                SET minutes_used = minutes_used + $1
                WHERE id = $2::uuid
                """,
                minutes,
                self.company_id,
            )
            memory_enabled = await self._get_memory_enabled()
            logger.info(f"Dialog finished: {self.dialog_id} ({duration_seconds:.1f}s)")
        except Exception as e:
            logger.warning(f"Failed to finish dialog tracking: {e}")
        finally:
            await self._close()

        # Trigger self-learning asynchronously (non-blocking)
        if memory_enabled:
            asyncio.ensure_future(
                learn_from_dialog(
                    dialog_id=self.dialog_id,
                    company_id=self.company_id,
                    messages=list(self._messages),
                )
            )

    def _extract_topics(self) -> list[str]:
        """Simple keyword-based topic extraction from conversation."""
        topic_keywords = {
            "цены": ["цена", "стоит", "стоимость", "прайс", "сколько", "рублей", "₽"],
            "запись": ["запись", "записаться", "записать", "запишите", "приём"],
            "расписание": ["расписание", "часы", "работает", "время", "когда", "открыт"],
            "врачи": ["врач", "доктор", "специалист", "терапевт", "ортодонт"],
            "услуги": ["услуг", "процедур", "лечение", "делаете"],
            "адрес": ["адрес", "находится", "как добраться", "ехать"],
        }
        found = set()
        all_text = " ".join(
            m["content"].lower() for m in self._messages if m["role"] == "user"
        )
        for topic, keywords in topic_keywords.items():
            if any(kw in all_text for kw in keywords):
                found.add(topic)
        return list(found)

    async def _close(self):
        if self._conn and not self._conn.is_closed():
            await self._conn.close()
            self._conn = None
