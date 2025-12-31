"""
Run Alembic migrations with sync psycopg2 connection.
"""
import os
from alembic.config import Config
from alembic import command

# Force sync postgresql URL for migrations
db_url = os.getenv("DATABASE_URL", "")
sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

# Create Alembic config
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

# Run migrations
print(f"Running migrations with URL: {sync_url.split('@')[0]}@...")
command.upgrade(alembic_cfg, "head")
print("✅ Migrations completed successfully")
