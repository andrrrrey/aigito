#!/usr/bin/env python3
"""
Usage:
    python make_admin.py user@example.com
"""
import asyncio
import sys

from sqlalchemy import select

from database import AsyncSessionLocal
from auth.models import User


async def make_admin(email: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Error: user '{email}' not found.")
            sys.exit(1)
        user.is_superuser = True
        await db.commit()
        print(f"OK: '{email}' is now an admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)
    asyncio.run(make_admin(sys.argv[1]))
