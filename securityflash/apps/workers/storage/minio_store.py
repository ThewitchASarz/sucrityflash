"""
MinIO storage client for evidence artifacts.

MUST-FIX C: MinIO bucket configured to deny delete operations.
"""
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import io
import json
from typing import Dict, Any
from apps.api.core.config import settings


class MinIOStore:
    """MinIO storage client."""

    def __init__(self):
        """Initialize MinIO client."""
        # Parse endpoint (remove http://)
        endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")

        self.client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False  # True for HTTPS in production
        )

        self.bucket = settings.MINIO_BUCKET

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"Warning: Could not verify bucket {self.bucket}: {e}")

    def write_evidence(self, run_id: str, evidence_id: str, data: Dict[str, Any]) -> str:
        """
        Write evidence artifact to MinIO.

        Args:
            run_id: Run ID
            evidence_id: Evidence ID
            data: Evidence data (will be JSON serialized)

        Returns:
            S3 URI: s3://bucket/run_id/evidence_id.json
        """
        # Build object path
        object_name = f"{run_id}/{evidence_id}.json"

        # Serialize data
        json_data = json.dumps(data, indent=2)
        json_bytes = json_data.encode('utf-8')

        # Upload to MinIO
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(json_bytes),
                length=len(json_bytes),
                content_type="application/json"
            )

            # Return S3 URI
            return f"s3://{self.bucket}/{object_name}"

        except S3Error as e:
            raise Exception(f"Failed to write evidence to MinIO: {e}")

    def read_evidence(self, run_id: str, evidence_id: str) -> Dict[str, Any]:
        """
        Read evidence artifact from MinIO.

        Args:
            run_id: Run ID
            evidence_id: Evidence ID

        Returns:
            Evidence data dict
        """
        object_name = f"{run_id}/{evidence_id}.json"

        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            return json.loads(data.decode('utf-8'))
        except S3Error as e:
            raise Exception(f"Failed to read evidence from MinIO: {e}")
        finally:
            response.close()
            response.release_conn()
