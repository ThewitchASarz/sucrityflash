"""
Integration configuration model for external system connections.
"""
from sqlalchemy import Column, String, Boolean, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from database import Base
import uuid
import enum


class IntegrationType(str, enum.Enum):
    """Integration types."""
    SLACK = "slack"
    JIRA = "jira"
    WEBHOOK = "webhook"


class IntegrationConfig(Base):
    """
    Configuration for external integrations.

    CRITICAL: Integrations are for notifications/ticketing ONLY.
    Never used for orchestration, tool execution, or policy decisions.
    """
    __tablename__ = "integration_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Integration type
    type = Column(SQLEnum(IntegrationType), nullable=False, index=True)

    # Configuration (encrypted in production)
    config = Column(JSONB, nullable=False)
    # Example for Slack: {"webhook_url": "https://hooks.slack.com/...", "channel": "#security"}
    # Example for Jira: {"url": "https://jira.example.com", "api_token": "...", "project_key": "SEC"}
    # Example for Webhook: {"url": "https://api.example.com/webhooks", "secret": "...", "events": ["run_complete"]}

    # Status
    enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<IntegrationConfig(id={self.id}, type={self.type}, enabled={self.enabled})>"
