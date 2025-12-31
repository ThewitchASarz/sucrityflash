"""
Evidence service - MUST-FIX C: No delete operations.

Evidence is immutable once written. No delete() or update() methods exist.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from apps.api.models.evidence import Evidence
from datetime import datetime
import uuid


class EvidenceService:
    """
    Evidence service with immutability enforcement.

    MUST-FIX C: NO delete() method. NO update() method.
    Evidence can only be created and retrieved.
    """

    @staticmethod
    def create(
        db: Session,
        run_id: uuid.UUID,
        evidence_type: str,
        artifact_uri: str,
        artifact_hash: str,
        generated_by: str,
        evidence_metadata: dict
    ) -> Evidence:
        """
        Create new evidence record.

        Args:
            db: Database session
            run_id: Associated run ID
            evidence_type: Type of evidence (command_output, llm_response, etc.)
            artifact_uri: S3 URI to artifact
            artifact_hash: SHA256 hash of artifact
            generated_by: Generator (worker, agent_id)
            evidence_metadata: Evidence metadata (tool_used, returncode, etc.)

        Returns:
            Created Evidence instance
        """
        evidence = Evidence(
            run_id=run_id,
            evidence_type=evidence_type,
            artifact_uri=artifact_uri,
            artifact_hash=artifact_hash,
            generated_by=generated_by,
            generated_at=datetime.utcnow(),
            validation_status="PENDING",
            evidence_metadata=evidence_metadata
        )

        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        return evidence

    @staticmethod
    def get(db: Session, evidence_id: uuid.UUID) -> Optional[Evidence]:
        """
        Get evidence by ID.

        Args:
            db: Database session
            evidence_id: Evidence ID

        Returns:
            Evidence instance or None
        """
        return db.query(Evidence).filter(Evidence.id == evidence_id).first()

    @staticmethod
    def list_by_run(db: Session, run_id: uuid.UUID) -> List[Evidence]:
        """
        List all evidence for a run.

        Args:
            db: Database session
            run_id: Run ID

        Returns:
            List of Evidence instances
        """
        return db.query(Evidence).filter(Evidence.run_id == run_id).all()

    # ❌ delete() does NOT exist (MUST-FIX C)
    # ❌ update() does NOT exist (MUST-FIX C)
