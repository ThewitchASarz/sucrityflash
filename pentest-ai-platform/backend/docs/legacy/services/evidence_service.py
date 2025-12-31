"""
Evidence service: Hash-chained, immutable evidence storage with S3 upload.
"""
import boto3
from datetime import datetime
from typing import Optional
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.evidence import Evidence
from utils.hashing import sha256_hash, sha256_hash_dict
from utils.crypto import RSAKeyManager
from config import settings


class EvidenceService:
    """Service for creating and verifying hash-chained evidence."""

    def __init__(self):
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
        self.bucket = settings.S3_BUCKET

    async def create_evidence(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        action_id: str,
        evidence_type: str,
        content: dict,
        metadata: dict,
        actor_type: str,
        actor_id: uuid.UUID,
        signature: Optional[str] = None
    ) -> Evidence:
        """
        Create new evidence with hash chaining.

        Args:
            db: Database session
            run_id: Run ID
            action_id: Action ID
            evidence_type: Type (tool_output, screenshot, log, etc.)
            content: Evidence content (dict)
            metadata: Additional metadata
            actor_type: "USER" or "AGENT"
            actor_id: Actor UUID
            signature: Optional digital signature

        Returns:
            Evidence: Created evidence record

        Process:
            1. Serialize content deterministically
            2. Hash content (SHA-256)
            3. Get prior evidence hash (for chaining)
            4. Upload content to S3 (WORM)
            5. Create evidence record with hashes
        """
        # 1. Serialize content deterministically
        content_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
        content_hash = sha256_hash(content_json)

        # 2. Get prior evidence hash (last evidence for this run)
        prior_evidence_hash = await self._get_last_evidence_hash(db, run_id)

        # 3. Upload to S3
        s3_path = f"runs/{run_id}/evidence/{uuid.uuid4()}.json"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_path,
                Body=content_json,
                ContentType='application/json',
                Metadata={
                    'run_id': str(run_id),
                    'action_id': action_id,
                    'evidence_type': evidence_type,
                    'content_hash': content_hash
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upload evidence to S3: {str(e)}")

        # 4. Create evidence record
        evidence = Evidence(
            run_id=run_id,
            action_id=action_id,
            evidence_type=evidence_type,
            content_hash=content_hash,
            prior_evidence_hash=prior_evidence_hash,
            s3_path=s3_path,
            metadata=metadata,
            created_by_actor_type=actor_type,
            created_by_actor_id=actor_id,
            signature=signature
        )

        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)

        return evidence

    async def _get_last_evidence_hash(
        self,
        db: AsyncSession,
        run_id: uuid.UUID
    ) -> Optional[str]:
        """Get hash of last evidence in chain for this run."""
        result = await db.execute(
            select(Evidence)
            .where(Evidence.run_id == run_id)
            .order_by(desc(Evidence.created_at))
            .limit(1)
        )
        last_evidence = result.scalar_one_or_none()

        return last_evidence.content_hash if last_evidence else None

    async def verify_evidence_chain(
        self,
        db: AsyncSession,
        run_id: uuid.UUID
    ) -> tuple[bool, Optional[str]]:
        """
        Verify integrity of evidence chain for a run.

        Args:
            db: Database session
            run_id: Run ID

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)

        Process:
            1. Fetch all evidence for run in chronological order
            2. Verify each evidence's prior_evidence_hash matches previous content_hash
            3. Verify content_hash matches actual content in S3
        """
        # Fetch all evidence in order
        result = await db.execute(
            select(Evidence)
            .where(Evidence.run_id == run_id)
            .order_by(Evidence.created_at)
        )
        evidence_chain = result.scalars().all()

        if not evidence_chain:
            return True, None

        # Verify chain integrity
        for i, evidence in enumerate(evidence_chain):
            # Check prior hash linkage
            if i == 0:
                # First evidence should have no prior
                if evidence.prior_evidence_hash is not None:
                    return False, f"First evidence {evidence.id} has unexpected prior_evidence_hash"
            else:
                # Subsequent evidence should link to previous
                expected_prior = evidence_chain[i - 1].content_hash
                if evidence.prior_evidence_hash != expected_prior:
                    return False, f"Evidence {evidence.id} has broken chain: expected prior {expected_prior}, got {evidence.prior_evidence_hash}"

            # Verify content hash against S3
            try:
                s3_obj = self.s3_client.get_object(Bucket=self.bucket, Key=evidence.s3_path)
                s3_content = s3_obj['Body'].read().decode('utf-8')
                computed_hash = sha256_hash(s3_content)

                if computed_hash != evidence.content_hash:
                    return False, f"Evidence {evidence.id} has content hash mismatch: expected {evidence.content_hash}, got {computed_hash}"
            except Exception as e:
                return False, f"Failed to verify evidence {evidence.id} against S3: {str(e)}"

        return True, None

    async def get_evidence_content(
        self,
        evidence: Evidence
    ) -> dict:
        """
        Retrieve evidence content from S3.

        Args:
            evidence: Evidence record

        Returns:
            dict: Evidence content
        """
        try:
            s3_obj = self.s3_client.get_object(Bucket=self.bucket, Key=evidence.s3_path)
            content_json = s3_obj['Body'].read().decode('utf-8')
            return json.loads(content_json)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve evidence from S3: {str(e)}")


# Global instance
evidence_service = EvidenceService()
