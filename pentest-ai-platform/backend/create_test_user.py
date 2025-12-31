#!/usr/bin/env python3
"""Create a test user directly in the database."""
import asyncio
from sqlalchemy import select
from database import async_session, engine
from models.user import User, UserRole
from services.auth_service import AuthService
import uuid

auth_service = AuthService()

async def create_user():
    """Create test user."""
    async with async_session() as session:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == "test@pentest.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"✓ User already exists: {existing_user.email}")
            print(f"  User ID: {existing_user.id}")
            return existing_user.id

        # Create new user
        hashed_password = auth_service.hash_password("Test123456")
        user = User(
            id=uuid.uuid4(),
            email="test@pentest.com",
            password_hash=hashed_password,
            full_name="Test Pentester",
            role=UserRole.COORDINATOR,
            is_active=True
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(f"✓ Created user: {user.email}")
        print(f"  User ID: {user.id}")
        print(f"  Password: Test123456")
        return user.id

if __name__ == "__main__":
    asyncio.run(create_user())
