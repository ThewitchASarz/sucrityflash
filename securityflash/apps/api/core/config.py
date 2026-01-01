"""
Configuration management using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    PORT: int = 8000

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str

    # OpenAI
    OPENAI_API_KEY: str

    # Security
    POLICY_SIGNING_SECRET: str
    SECRET_KEY: str

    # Logging
    LOG_LEVEL: str = "INFO"

    # Worker Configuration
    WORKER_POLL_INTERVAL_SEC: int = 5
    WORKER_TIMEOUT_SEC: int = 30
    WORKER_MAX_OUTPUT_KB: int = 50

    # Agent Configuration
    AGENT_MAX_ITERATIONS: int = 100
    AGENT_CHECKPOINT_INTERVAL: int = 5

    # Control Plane URL (used by agents/workers when not explicitly provided)
    CONTROL_PLANE_API_URL: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()
