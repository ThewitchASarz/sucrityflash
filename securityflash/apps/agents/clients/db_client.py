"""
Database client for agent checkpoints.

Agents use this to save/restore state for recovery.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Dict, Any, Optional
import logging
from apps.api.core.config import settings
from apps.api.models.agent_checkpoint import AgentCheckpoint
from apps.api.models.llm_call import LLMCall

logger = logging.getLogger(__name__)


class DBClient:
    """Direct database client for agents."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database client.

        Args:
            database_url: Database URL (defaults to settings.DATABASE_URL)
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def save_checkpoint(
        self,
        run_id: str,
        agent_id: str,
        iteration: int,
        state: str,
        memory: Dict[str, Any]
    ):
        """
        Save agent checkpoint.

        Args:
            run_id: Run ID
            agent_id: Agent ID
            iteration: Current iteration
            state: Agent state (running, paused, completed, failed)
            memory: Agent memory dict
        """
        db = self.get_session()
        try:
            # Check if checkpoint exists
            checkpoint = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.run_id == run_id,
                AgentCheckpoint.agent_id == agent_id
            ).first()

            if checkpoint:
                # Update existing
                checkpoint.iteration = iteration
                checkpoint.state = state
                checkpoint.memory_json = memory
            else:
                # Create new
                checkpoint = AgentCheckpoint(
                    run_id=run_id,
                    agent_id=agent_id,
                    iteration=iteration,
                    state=state,
                    memory_json=memory
                )
                db.add(checkpoint)

            db.commit()
            logger.info(f"Checkpoint saved: iteration {iteration}")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    def load_checkpoint(
        self,
        run_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load agent checkpoint.

        Args:
            run_id: Run ID
            agent_id: Agent ID

        Returns:
            Checkpoint dict or None
        """
        db = self.get_session()
        try:
            checkpoint = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.run_id == run_id,
                AgentCheckpoint.agent_id == agent_id
            ).first()

            if checkpoint:
                return {
                    "iteration": checkpoint.iteration,
                    "state": checkpoint.state,
                    "memory": checkpoint.memory_json
                }
            return None

        finally:
            db.close()

    def log_llm_call(
        self,
        run_id: str,
        agent_id: str,
        model: str,
        prompt_hash: str,
        response_hash: str,
        policy_version: str
    ):
        """
        Log LLM call for audit.

        Args:
            run_id: Run ID
            agent_id: Agent ID
            model: Model name
            prompt_hash: SHA256 of prompt
            response_hash: SHA256 of response
            policy_version: Policy version
        """
        db = self.get_session()
        try:
            llm_call = LLMCall(
                run_id=run_id,
                agent_id=agent_id,
                model=model,
                prompt_hash=prompt_hash,
                response_hash=response_hash,
                policy_version=policy_version
            )
            db.add(llm_call)
            db.commit()
            logger.debug(f"LLM call logged: {model}")

        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")
            db.rollback()
        finally:
            db.close()
