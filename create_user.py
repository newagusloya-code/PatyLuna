import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import async_session_factory, engine, Base
from app.db.models import User
from app.core.security import hash_password

async def main():
    # Make sure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Check if user already exists
        from sqlalchemy import select
        res = await session.execute(select(User).where(User.email == "captain@sleepwell.com"))
        if res.scalar_one_or_none():
            print("User already exists!")
            return

        user = User(
            email="captain@sleepwell.com",
            username="Captain",
            hashed_password=hash_password("TripleCheck123!")
        )
        session.add(user)
        await session.commit()
        print("User created successfully!")

asyncio.run(main())
