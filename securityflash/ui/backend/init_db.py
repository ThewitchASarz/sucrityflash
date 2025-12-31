"""
Database initialization script.
Ensures all models are loaded and tables created.
"""
import asyncio
from database import engine, Base
from config import settings

# Import all models to register them with SQLAlchemy
from models.user import User, UserSigningKey
from models.project import Project
from models.scope import Scope
from models.test_plan import TestPlan, Action
from models.run import Run
from models.approval import Approval
from models.evidence import Evidence
from models.finding import Finding
from models.audit_log import AuditLog


async def init_database():
    """Initialize database: create all tables."""
    print("Initializing database...")
    print(f"Database URL: {settings.DATABASE_URL}")

    async with engine.begin() as conn:
        # Drop all tables (careful in production!)
        if settings.ENVIRONMENT == "development":
            print("⚠️  Dropping all tables (development mode)...")
            await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Database initialized successfully")
    print(f"✓ Tables created: {len(Base.metadata.tables)}")
    print(f"✓ Table names: {', '.join(Base.metadata.tables.keys())}")


async def verify_models():
    """Verify all models are registered."""
    print("\nVerifying models...")

    models = [
        User,
        UserSigningKey,
        Project,
        Scope,
        TestPlan,
        Action,
        Run,
        Approval,
        Evidence,
        Finding,
        AuditLog
    ]

    for model in models:
        table_name = model.__tablename__
        if table_name in Base.metadata.tables:
            print(f"✓ {model.__name__} -> {table_name}")
        else:
            print(f"✗ {model.__name__} NOT REGISTERED")

    print(f"\n✓ Total models: {len(models)}")
    print(f"✓ Total tables: {len(Base.metadata.tables)}")


if __name__ == "__main__":
    asyncio.run(init_database())
    asyncio.run(verify_models())
