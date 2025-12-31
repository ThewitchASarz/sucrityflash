"""
Initialize database schema for SecurityFlash V1.
Creates all tables from SQLAlchemy models.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from apps.api.db.base import Base
from apps.api.db.session import engine

# Import all models to ensure they're registered
from apps.api.models.project import Project
from apps.api.models.scope import Scope
from apps.api.models.run import Run
from apps.api.models.action_spec import ActionSpec
from apps.api.models.approval import Approval
from apps.api.models.evidence import Evidence
from apps.api.models.audit_log import AuditLog
from apps.api.models.agent_checkpoint import AgentCheckpoint
from apps.api.models.llm_call import LLMCall

print("Creating all database tables...")
print(f"Database URL: {engine.url}")

try:
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")

    # List created tables
    print("\nCreated tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")

except Exception as e:
    print(f"❌ Error creating tables: {e}")
    sys.exit(1)
