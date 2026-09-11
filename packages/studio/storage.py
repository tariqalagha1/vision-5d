"""
Vision 5D — Studio Storage Abstraction
Unified write → metadata → read-back → hash verification through durable artifact system.
"""
import os, hashlib, json as _json, structlog
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from packages.domain.models import DurableArtifactRef
from packages.domain.database import SessionLocal

logger = structlog.get_logger()


class StudioStorageProvider:
    """Production-compatible storage adapter for Studio exports and artifacts."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(
            os.path.dirname(__file__), "..", "..", ".storage"
        )
        os.makedirs(self.base_path, exist_ok=True)

    def write_artifact(
        self,
        db: Session,
        tenant_id: UUID,
        project_id: UUID,
        artifact_type: str,
        data: bytes,
        mime_type: str = "application/octet-stream",
        producing_stage: str = "studio_export",
        producing_version: int = 1,
        storage_key_prefix: str = "",
    ) -> dict:
        """Write artifact bytes through the storage provider and persist metadata."""

        content_hash = hashlib.sha256(data).hexdigest()
        content_hash_str = str(content_hash)  # Explicit string conversion for DB
        storage_key = (
            f"{storage_key_prefix}/"
            f"v5d/{tenant_id}/projects/{project_id}/"
            f"{artifact_type}/v{producing_version}/{content_hash_str[:16]}"
        )

        # Write bytes to storage
        file_path = os.path.join(self.base_path, storage_key.replace("/", "_"))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)

        # Persist artifact metadata
        dart = DurableArtifactRef(
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=uuid4(),
            artifact_type=artifact_type,
            storage_provider="local",
            storage_key=storage_key,
            content_hash=content_hash,
            size_bytes=len(data),
            mime_type=mime_type,
            producing_stage=producing_stage,
            producing_version=producing_version,
        )
        db.add(dart)
        db.commit()
        db.refresh(dart)

        logger.info("artifact_written",
                    artifact_id=str(dart.id),
                    storage_key=storage_key,
                    size=len(data),
                    hash=content_hash[:16])

        return {
            "artifact_id": str(dart.id),
            "storage_provider": "local",
            "storage_key": storage_key,
            "size_bytes": len(data),
            "content_hash": content_hash,
            "mime_type": mime_type,
        }

    def read_artifact(self, db: Session, artifact_id) -> Optional[dict]:
        """Read artifact bytes back through the storage provider."""
        # Accept both UUID objects and string UUIDs
        from uuid import UUID as _UUID
        if isinstance(artifact_id, str):
            artifact_id = _UUID(artifact_id)
        dart = db.query(DurableArtifactRef).filter(
            DurableArtifactRef.id == artifact_id
        ).first()

        if not dart:
            return None

        # Read bytes from storage
        file_path = os.path.join(self.base_path, dart.storage_key.replace("/", "_"))
        if not os.path.exists(file_path):
            return {
                "artifact_id": str(dart.id),
                "error": f"File not found: {file_path}",
                "storage_key": dart.storage_key,
                "expected_hash": dart.content_hash,
            }

        with open(file_path, "rb") as f:
            data = f.read()

        read_hash = hashlib.sha256(data).hexdigest()
        hash_match = read_hash == dart.content_hash

        if not hash_match:
            logger.warn("hash_mismatch",
                       artifact_id=str(dart.id),
                       expected=dart.content_hash[:16],
                       actual=read_hash[:16])

        return {
            "artifact_id": str(dart.id),
            "storage_key": dart.storage_key,
            "size_bytes": len(data),
            "expected_hash": dart.content_hash,
            "read_back_hash": read_hash,
            "hash_match": hash_match,
            "data": data if hash_match else None,
        }

    def verify_artifact(
        self,
        db: Session,
        artifact_id: UUID,
        expected_hash: str = None,
    ) -> dict:
        """Full verification: read back + hash check + optional expected hash."""
        result = self.read_artifact(db, artifact_id)
        if result is None:
            return {"verified": False, "error": "Artifact not found"}
        if result.get("error"):
            return {"verified": False, "error": result["error"]}

        verified = result.get("hash_match", False)
        if expected_hash and result.get("read_back_hash") != expected_hash:
            verified = False

        return {
            "verified": verified,
            "artifact_id": str(artifact_id),
            "storage_key": result["storage_key"],
            "size_bytes": result["size_bytes"],
            "expected_hash": expected_hash or result["expected_hash"],
            "read_back_hash": result["read_back_hash"],
            "hash_match": result["hash_match"],
        }

    def list_artifacts(self, db: Session, project_id: UUID, tenant_id: UUID) -> list[dict]:
        """List all artifacts for a project."""
        artifacts = db.query(DurableArtifactRef).filter(
            DurableArtifactRef.project_id == project_id,
            DurableArtifactRef.tenant_id == tenant_id,
        ).all()
        return [{
            "artifact_id": str(a.id),
            "artifact_type": a.artifact_type,
            "storage_key": a.storage_key,
            "content_hash": a.content_hash,
            "size_bytes": a.size_bytes,
            "mime_type": a.mime_type,
            "producing_stage": a.producing_stage,
            "producing_version": a.producing_version,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in artifacts]


# Singleton
storage_provider = StudioStorageProvider()
