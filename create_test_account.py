import asyncio
from app.db.database import async_session_factory
from app.db.models import User
from app.core.security import hash_password
from sqlalchemy import select

async def create():
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == "paty@test.com"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Test user already exists.")
            return
        
        user = User(
            email="paty@test.com",
            username="Paty Luna",
            hashed_password=hash_password("PatyLuna123!"),
            is_active=True,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        print("Test user created successfully! Email: paty@test.com, Password: PatyLuna123!")

if __name__ == "__main__":
    asyncio.run(create())
