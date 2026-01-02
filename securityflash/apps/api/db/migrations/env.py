"""
Alembic environment configuration.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[4]))

from apps.api.db.base import Base
from apps.api.core.config import settings

# Import all models to ensure they're registered with Base
from apps.api.models.project import Project
from apps.api.models.scope import Scope
from apps.api.models.run import Run
from apps.api.models.action_spec import ActionSpec
from apps.api.models.approval import Approval
from apps.api.models.evidence import Evidence
from apps.api.models.audit_log import AuditLog
from apps.api.models.agent_checkpoint import AgentCheckpoint
from apps.api.models.llm_call import LLMCall
from apps.api.models.validation_pack import ValidationPack
from apps.api.models.swarm_task import SwarmTask
from apps.api.models.swarm_lock import SwarmLock
from apps.api.models.swarm_budget import SwarmBudget

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

# Override sqlalchemy.url with environment variable
# Convert asyncpg URL to psycopg2 for Alembic migrations
database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
