"""
Vision 5D — Phase 4 3D Scene API Routes
Async durable 3D reconstruction endpoint + scene retrieval + GLB export.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
import structlog, hashlib, json as _json

from packages.domain.database import get_db, SessionLocal
from packages.domain.models import (
    DurableJob as DurableJobModel,
    PersistedGeometry,
    UnderstandingGraph,
)
from packages.contracts.models import (
    JobState, JobSubmitResponse, DurableJob as DurableJobSchema,
)
from packages.domain.models import Scene3DVersion, Scene3DObject, Scene3DMesh

router = APIRouter(prefix="/api/v4", tags=["Phase 4 — 3D Scene"])
logger = structlog.get_logger()


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    from apps.api.main import get_current_user
    return get_current_user(request)


def _submit_durable_job(
    db: Session, tenant_id: UUID, workspace_id: UUID, project_id: UUID,
    job_type: str, params: dict, idempotency_key: Optional[str] = None,
) -> DurableJobModel:
    """Create a durable job with idempotency protection."""
    key = idempotency_key or f"{tenant_id}:{project_id}:{job_type}:{hashlib.sha256(str(params).encode()).hexdigest()[:16]}"

    existing = db.query(DurableJobModel).filter(
        DurableJobModel.idempotency_key == key
    ).first()
    if existing:
        return existing

    param_hash = hashlib.sha256(str(params).encode()).hexdigest()[:16]
    duplicate = db.query(DurableJobModel).filter(
        DurableJobModel.project_id == project_id,
        DurableJobModel.tenant_id == tenant_id,
        DurableJobModel.job_type == job_type,
        DurableJobModel.param_hash == param_hash,
        ~DurableJobModel.state.in_([
            JobState.FAILED_TERMINAL.value, JobState.CANCELLED.value, JobState.EXPIRED.value
        ])
    ).first()
    if duplicate:
        return duplicate

    job = DurableJobModel(
        tenant_id=tenant_id, workspace_id=workspace_id, project_id=project_id,
        job_type=job_type, idempotency_key=key, params=params,
        param_hash=param_hash, state=JobState.AUTHORIZED.value, initiated_by="user",
    )
    db.add(job)
    db.flush()
    job.state = JobState.QUEUED.value
    db.commit()
    db.refresh(job)
    logger.info("scene3d_job_submitted", job_id=str(job.id))
    return job


# ═══════════════════════════════════════════════════════════
# 3D Reconstruction
# ═══════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/scene/reconstruct", response_model=JobSubmitResponse)
async def scene3d_reconstruct(
    project_id: UUID,
    request: Request,
    geometry_model_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    """Submit 3D scene reconstruction as a durable job. Returns immediately."""
    user_id, tenant_id = _get_user_tenant(request)
    ws_id = workspace_id or UUID("00000000-0000-0000-0000-00000000000a")

    # Find authoritative geometry model
    if geometry_model_id:
        geom = db.query(PersistedGeometry).filter(
            PersistedGeometry.id == geometry_model_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).first()
    else:
        geom = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).order_by(PersistedGeometry.version.desc()).first()

    if not geom:
        raise HTTPException(404, "No geometry model found. Run geometry reconstruction first.")

    params = {
        "project_id": str(project_id),
        "geometry_model_id": str(geom.id),
        "geometry_version": geom.version,
        "source_graph_id": str(geom.source_graph_id) if geom.source_graph_id else None,
        "source_graph_version": geom.source_graph_version,
    }

    idempotency_key = f"{tenant_id}:{project_id}:3d-reconstruction:{geom.id}:{geom.version}"
    job = _submit_durable_job(
        db=db, tenant_id=tenant_id, workspace_id=ws_id,
        project_id=project_id, job_type="3d-reconstruction",
        params=params, idempotency_key=idempotency_key,
    )

    return JobSubmitResponse(
        job_id=job.id, state=JobState(job.state),
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        status_endpoint=f"/api/v1/jobs/{job.id}",
    )


# ═══════════════════════════════════════════════════════════
# Scene Retrieval
# ═══════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/scene")
async def get_scene(project_id: UUID, request: Request, version: int = None):
    """Get the latest (or specified) 3D scene version for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        query = db.query(Scene3DVersion).filter(
            Scene3DVersion.project_id == project_id,
            Scene3DVersion.tenant_id == tenant_id,
        )
        if version:
            query = query.filter(Scene3DVersion.version == version)
        else:
            query = query.order_by(Scene3DVersion.version.desc())

        scene = query.first()
        if not scene:
            raise HTTPException(404, "No 3D scene found. Run 3D reconstruction first.")

        objects = db.query(Scene3DObject).filter(Scene3DObject.scene_id == scene.id).all()
        meshes = db.query(Scene3DMesh).filter(Scene3DMesh.scene_id == scene.id).all()

        # Check staleness
        latest_geom = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).order_by(PersistedGeometry.version.desc()).first()
        is_stale = latest_geom and latest_geom.version != scene.source_geometry_version

        return {
            "scene_id": str(scene.id),
            "project_id": str(project_id),
            "version": scene.version,
            "state": scene.state,
            "is_complete": scene.is_complete,
            "is_stale": is_stale,
            "lineage": scene.lineage,
            "source_geometry_version": scene.source_geometry_version,
            "source_graph_version": scene.source_graph_version,
            "coordinate_system": scene.coordinate_system,
            "unit_system": scene.unit_system,
            "statistics": scene.statistics,
            "bbox": {
                "min": [scene.bbox_min_x, scene.bbox_min_y, scene.bbox_min_z],
                "max": [scene.bbox_max_x, scene.bbox_max_y, scene.bbox_max_z],
            } if scene.bbox_min_x is not None else None,
            "objects": [{
                "id": str(o.id), "type": o.object_type, "label": o.label,
                "properties": o.properties, "visible": o.visible,
            } for o in objects],
            "meshes": [{
                "id": str(m.id), "object_type": m.object_type,
                "vertex_count": m.vertex_count, "triangle_count": m.triangle_count,
                "is_valid": m.is_valid,
                "validation_issues": m.validation_issues,
            } for m in meshes],
            "validation": {
                "issues": scene.completeness_issues or [],
                "total": len(scene.completeness_issues or []),
                "is_clean": len(scene.completeness_issues or []) == 0,
            },
            "created_at": scene.created_at.isoformat() if scene.created_at else None,
            "updated_at": scene.updated_at.isoformat() if scene.updated_at else None,
        }
    finally:
        db.close()


@router.get("/projects/{project_id}/scene/versions")
async def scene_versions(project_id: UUID, request: Request):
    """List all 3D scene versions for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        versions = db.query(Scene3DVersion).filter(
            Scene3DVersion.project_id == project_id,
            Scene3DVersion.tenant_id == tenant_id,
        ).order_by(Scene3DVersion.version.desc()).all()

        return {
            "project_id": str(project_id),
            "versions": [{
                "scene_id": str(v.id),
                "version": v.version,
                "state": v.state,
                "is_complete": v.is_complete,
                "lineage": v.lineage,
                "vertex_count": v.vertex_count,
                "triangle_count": v.triangle_count,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            } for v in versions],
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# GLB Export
# ═══════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/scene/export/glb")
async def export_scene_glb(project_id: UUID, request: Request, version: int = None):
    """Export the scene as a GLB file."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        query = db.query(Scene3DVersion).filter(
            Scene3DVersion.project_id == project_id,
            Scene3DVersion.tenant_id == tenant_id,
        )
        if version:
            query = query.filter(Scene3DVersion.version == version)
        else:
            query = query.order_by(Scene3DVersion.version.desc())

        scene = query.first()
        if not scene:
            raise HTTPException(404, "No 3D scene found")

        # Reconstruct scene from stored data + generate GLB
        scene_data = scene.scene_data or {}
        if not scene_data.get("meshes"):
            raise HTTPException(400, "Scene has no mesh data for export")

        # Build Scene3D from persisted data
        from packages.scene3d.contracts import Scene3D, SceneStatistics
        from packages.scene3d.glb_export import export_glb, validate_glb

        try:
            recon_scene = Scene3D(**scene_data)
            glb_bytes = export_glb(recon_scene)
            validation = validate_glb(glb_bytes)

            headers = {
                "Content-Disposition": f"attachment; filename=vision5d_scene_v{scene.version}.glb",
                "X-Scene-Version": str(scene.version),
                "X-GLB-Valid": str(validation.get("valid", False)),
                "X-GLB-SHA256": validation.get("sha256", ""),
                "X-GLB-Size": str(len(glb_bytes)),
            }
            return Response(content=glb_bytes, media_type="model/gltf-binary", headers=headers)
        except Exception as e:
            raise HTTPException(500, f"GLB export failed: {e}")
    finally:
        db.close()
