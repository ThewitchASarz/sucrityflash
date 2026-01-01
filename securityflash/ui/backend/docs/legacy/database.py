"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class for all models
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# Dependency for FastAPI routes
async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.

    Usage in FastAPI:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Query users from database
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
