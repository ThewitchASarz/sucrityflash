"""
Signature verification service for digital signatures.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import UserSigningKey
from utils.crypto import rsa_manager
from utils.hashing import sha256_hash_dict
import uuid
from typing import Optional


class SignatureService:
    """Service for verifying digital signatures."""

    @staticmethod
    async def verify_user_signature(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: str,
        signature: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verify user's RSA signature.

        Args:
            db: Database session
            user_id: User ID
            data: Data that was signed
            signature: Hex-encoded signature

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Get user's active signing keys
        result = await db.execute(
            select(UserSigningKey)
            .where(UserSigningKey.user_id == user_id)
            .where(UserSigningKey.revoked_at.is_(None))
            .order_by(UserSigningKey.created_at.desc())
        )
        keys = result.scalars().all()

        if not keys:
            return False, "No active signing keys found for user"

        # Try each key (user might have multiple keys)
        for key in keys:
            try:
                if rsa_manager.verify_signature(key.public_key, data, signature):
                    return True, None
            except Exception:
                continue

        return False, "Signature verification failed"

    @staticmethod
    def create_scope_content_hash(scope_data: dict) -> str:
        """
        Create deterministic hash of scope content for signature verification.

        Args:
            scope_data: Scope data (target_systems, excluded_systems, forbidden_methods, roe)

        Returns:
            str: SHA-256 hash of scope content
        """
        # Create deterministic representation of scope
        canonical_scope = {
            "target_systems": sorted(scope_data.get("target_systems", [])),
            "excluded_systems": sorted(scope_data.get("excluded_systems", [])),
            "forbidden_methods": sorted(scope_data.get("forbidden_methods", [])),
            "roe": scope_data.get("roe", {})
        }
        return sha256_hash_dict(canonical_scope)


# Global instance
signature_service = SignatureService()
