"""
Vision 5D — Phase 3 Geometry API Routes (Async Durable Job Model)
All pipeline execution now happens asynchronously through the worker.
API routes persist jobs and return immediately.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
import structlog, hashlib

from packages.domain.models import (
    DurableJob as DurableJobModel,
    PersistedGeometry, UnderstandingGraph,
    GeometryFloor, GeometryWall, GeometryRoom, GeometryOpening, GeometryEdit,
    ProgressEvent as ProgressEventModel,
    Checkpoint,
)
from packages.domain.database import SessionLocal, get_db
from packages.domain.persistence import (
    load_geometry_model, list_geometry_versions, persist_geometry_edit,
)
from packages.contracts.models import (
    JobState, JobSubmitResponse, DurableJob as DurableJobSchema,
    JobStatus, ProgressEvent,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v3", tags=["geometry"])
logger = structlog.get_logger()


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    """Extract user_id and tenant_id from session."""
    from apps.api.main import get_current_user
    return get_current_user(request)


def _submit_durable_job(
    db: Session, tenant_id: UUID, workspace_id: UUID, project_id: UUID,
    job_type: str, params: dict, idempotency_key: Optional[str] = None,
) -> DurableJobModel:
    """Create a durable job and submit it to the queue with idempotency protection."""
    if idempotency_key:
        existing = db.query(DurableJobModel).filter(
            DurableJobModel.idempotency_key == idempotency_key
        ).first()
        if existing:
            return existing

    param_hash = hashlib.sha256(str(params).encode()).hexdigest()[:16]

    # Check for duplicate active/completed job
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

    key = idempotency_key or f"{tenant_id}:{project_id}:{job_type}:{param_hash}"
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
    logger.info("durable_job_submitted", job_id=str(job.id), job_type=job_type)
    return job


# ═══════════════════════════════════════════════════════════
# Async Geometry Reconstruction (NEW — durable job model)
# ═══════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/geometry/reconstruct", response_model=JobSubmitResponse)
async def geometry_reconstruct_async(
    project_id: UUID,
    request: Request,
    workspace_id: Optional[UUID] = None,
    source_graph_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    """Submit geometry reconstruction as a durable job. Returns immediately.
    The worker executes Phase 2→Phase 3 independently.
    """
    user_id, tenant_id = _get_user_tenant(request)
    ws_id = workspace_id or UUID("00000000-0000-0000-0000-00000000000a")

    # Use existing graph if available
    graph_ref = None
    if source_graph_id:
        graph_ref = str(source_graph_id)
    else:
        last_graph = db.query(UnderstandingGraph).filter(
            UnderstandingGraph.project_id == project_id,
            UnderstandingGraph.tenant_id == tenant_id,
        ).order_by(UnderstandingGraph.version.desc()).first()
        if last_graph:
            graph_ref = str(last_graph.id)

    params = {
        "project_id": str(project_id),
        "source_asset_id": str(uuid4()),  # Production: real asset reference
        "graph_id": graph_ref,
    }

    idempotency_key = f"{tenant_id}:{project_id}:geometry-reconstruction:{hashlib.sha256(str(graph_ref or '').encode()).hexdigest()[:16]}"

    job = _submit_durable_job(
        db=db, tenant_id=tenant_id, workspace_id=ws_id,
        project_id=project_id, job_type="geometry-reconstruction",
        params=params, idempotency_key=idempotency_key,
    )

    return JobSubmitResponse(
        job_id=job.id,
        state=JobState(job.state),
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        status_endpoint=f"/api/v1/jobs/{job.id}",
    )


# ═══════════════════════════════════════════════════════════
# Job Status & Progress
# ═══════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/geometry/progress")
async def geometry_progress(project_id: UUID, request: Request):
    """Get job progress from persisted state (polling endpoint). Supports reload."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        # Find active or most recent geometry job
        job = db.query(DurableJobModel).filter(
            DurableJobModel.project_id == project_id,
            DurableJobModel.tenant_id == tenant_id,
            DurableJobModel.job_type == "geometry-reconstruction",
        ).order_by(DurableJobModel.created_at.desc()).first()

        if not job:
            return {"status": "no_job", "events": []}

        events = db.query(ProgressEventModel).filter(
            ProgressEventModel.job_id == job.id
        ).order_by(ProgressEventModel.timestamp.desc()).limit(20).all()

        # Also check checkpoint records
        checkpoints = db.query(Checkpoint).filter(
            Checkpoint.job_id == job.id
        ).order_by(Checkpoint.sequence.desc()).limit(5).all()

        # Check if there's an output model
        model = db.query(PersistedGeometry).filter(
            PersistedGeometry.job_id == job.id
        ).order_by(PersistedGeometry.version.desc()).first()

        return {
            "job_id": str(job.id),
            "state": job.state,
            "progress_pct": events[0].progress_pct if events else 0.0,
            "current_stage": events[0].current_stage if events else None,
            "message": events[0].message if events else None,
            "events": [{
                "status": e.status,
                "progress_pct": e.progress_pct,
                "message": e.message,
                "stage": e.current_stage,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            } for e in reversed(events)],
            "checkpoints": [{
                "sequence": c.sequence,
                "current_stage": c.current_stage,
                "completed_stages": c.completed_stages,
                "resume_compatible": c.resume_compatible,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in checkpoints],
            "has_output": model is not None,
            "output_version": model.version if model else None,
        }
    finally:
        db.close()


@router.get("/projects/{project_id}/geometry/job")
async def geometry_job_status(project_id: UUID, request: Request):
    """Get the current or latest geometry job status."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        job = db.query(DurableJobModel).filter(
            DurableJobModel.project_id == project_id,
            DurableJobModel.tenant_id == tenant_id,
            DurableJobModel.job_type == "geometry-reconstruction",
        ).order_by(DurableJobModel.created_at.desc()).first()

        if not job:
            # Fall back to checking PersistedGeometry
            model = db.query(PersistedGeometry).filter(
                PersistedGeometry.project_id == project_id
            ).order_by(PersistedGeometry.version.desc()).first()
            if model:
                return {
                    "job_id": str(model.job_id) if model.job_id else None,
                    "model_id": str(model.id),
                    "project_id": str(project_id),
                    "status": model.state,
                    "version": model.version,
                    "is_complete": model.is_complete,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                }
            raise HTTPException(404, "No geometry job found")

        return {
            "job_id": str(job.id),
            "project_id": str(project_id),
            "status": job.state,
            "job_type": job.job_type,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Geometry Model Retrieval (unchanged — reads from persisted DB)
# ═══════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/geometry/model")
async def get_geometry_model(project_id: UUID, request: Request, version: int = None):
    """Get the full geometry model. Optionally specify version."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        query = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        )
        if version:
            query = query.filter(PersistedGeometry.version == version)
        else:
            query = query.order_by(PersistedGeometry.version.desc())

        model_db = query.first()
        if not model_db:
            raise HTTPException(404, "No geometry model found. Run reconstruction first.")

        data = load_geometry_model(db, model_db.id)
        if not data:
            raise HTTPException(404, "Geometry model data not found")

        floor_data = data["floors"][0] if data["floors"] else None

        # Adaptive area precision for rooms
        def format_area_m2(area: float) -> str:
            if area is None or area < 0:
                return "0.00"
            if area == 0:
                return "0.00"
            if area >= 1.0:
                return f"{area:.2f}"
            elif area >= 0.01:
                return f"{area:.4f}"
            else:
                return f"{area:.6f}"

        return {
            "project_id": str(project_id),
            "model_id": str(model_db.id),
            "version": model_db.version,
            "state": model_db.state,
            "is_complete": model_db.is_complete,
            "source_graph_id": str(model_db.source_graph_id) if model_db.source_graph_id else None,
            "source_graph_version": model_db.source_graph_version,
            "calibration": {
                "pixels_per_mm": model_db.scale_px_per_mm,
                "scale_ratio": model_db.scale_ratio,
                "confidence": model_db.scale_confidence,
                "units": model_db.units,
            },
            "floor": {
                "walls": [{
                    "id": str(w.id),
                    "centerline": w.centerline,
                    "thickness_mm": w.thickness_mm,
                    "is_external": w.is_external,
                    "state": w.state,
                } for w in (floor_data["walls"] if floor_data else [])],
                "rooms": [{
                    "id": str(r.id),
                    "label": r.label,
                    "function": r.function,
                    "area_mm2": r.area_mm2,
                    "area_m2": r.area_m2,
                    "area_m2_display": format_area_m2(r.area_m2),
                    "polygon": r.polygon,
                    "is_closed": r.is_closed,
                    "adjacent_to": r.adjacent_room_ids,
                } for r in (floor_data["rooms"] if floor_data else [])],
                "openings": [{
                    "id": str(o.id),
                    "type": o.opening_type,
                    "width_mm": o.width_mm,
                    "host_wall_id": str(o.host_wall_id) if o.host_wall_id else None,
                    "position_along_wall": o.position_along_wall,
                    "is_valid": o.is_valid,
                    "issues": o.validation_issues,
                } for o in (floor_data["openings"] if floor_data else [])],
            },
            "edits": [{
                "edit_type": e.edit_type,
                "version_before": e.version_before,
                "version_after": e.version_after,
                "applied_at": e.applied_at.isoformat() if e.applied_at else None,
            } for e in (data.get("edits") or [])] if data.get("edits") else [],
        }
    finally:
        db.close()


@router.get("/projects/{project_id}/geometry/validation")
async def get_validation_issues(project_id: UUID, request: Request):
    """Get validation issues for the latest geometry model."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        model = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).order_by(PersistedGeometry.version.desc()).first()

        if not model:
            return {"issues": [], "note": "No geometry model found"}

        data = load_geometry_model(db, model.id)
        if not data:
            return {"issues": [], "note": "No data"}

        issues = []
        for fdata in data["floors"]:
            for o in fdata.get("openings", []):
                if not o.is_valid:
                    for issue in (o.validation_issues or []):
                        issues.append({"object": f"opening/{o.id}", "issue": issue})
            for r in fdata.get("rooms", []):
                if not r.is_closed:
                    issues.append({"object": f"room/{r.id}", "issue": f"Room '{r.label}' not closed"})

        return {
            "total": len(issues),
            "model_version": model.version,
            "is_complete": model.is_complete,
            "issues": issues,
        }
    finally:
        db.close()


@router.get("/projects/{project_id}/geometry/versions")
async def geometry_versions(project_id: UUID, request: Request):
    """Get geometry model version history."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        versions = list_geometry_versions(db, project_id, tenant_id)
        return {
            "project_id": str(project_id),
            "versions": [{
                "model_id": str(v.id),
                "version": v.version,
                "state": v.state,
                "is_complete": v.is_complete,
                "source_graph_version": v.source_graph_version,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "updated_at": v.updated_at.isoformat() if v.updated_at else None,
            } for v in versions],
        }
    finally:
        db.close()


@router.get("/projects/{project_id}/geometry/evidence")
async def geometry_evidence(project_id: UUID, request: Request):
    """Get geometry reconstruction evidence with lineage."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        model = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).order_by(PersistedGeometry.version.desc()).first()

        if not model:
            raise HTTPException(404, "No geometry model found")

        graph = None
        if model.source_graph_id:
            graph = db.query(UnderstandingGraph).filter(
                UnderstandingGraph.id == model.source_graph_id).first()

        return {
            "project_id": str(project_id),
            "model_id": str(model.id),
            "model_version": model.version,
            "source_graph_id": str(model.source_graph_id) if model.source_graph_id else None,
            "source_graph_version": model.source_graph_version,
            "calibration": {
                "px_per_mm": model.scale_px_per_mm,
                "scale_ratio": model.scale_ratio,
                "confidence": model.scale_confidence,
            },
            "graph_metadata": graph.graph_metadata if graph else None,
            "lineage": f"graph_v{model.source_graph_version} → geometry_v{model.version}",
        }
    finally:
        db.close()


@router.post("/projects/{project_id}/geometry/edit")
async def apply_geometry_edit(project_id: UUID, request: Request):
    """Apply a geometry edit and persist to DB."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    edit_type = body.get("edit_type", "")
    params = body.get("params", {})

    db = SessionLocal()
    try:
        model = db.query(PersistedGeometry).filter(
            PersistedGeometry.project_id == project_id,
            PersistedGeometry.tenant_id == tenant_id,
        ).order_by(PersistedGeometry.version.desc()).first()

        if not model:
            raise HTTPException(404, "No geometry model found")

        version_before = model.version
        edit_db = persist_geometry_edit(
            db, model.id, edit_type,
            object_ref=UUID(body.get("wall_id")) if body.get("wall_id") else None,
            params=params,
            version_before=version_before,
            version_after=version_before + 1,
        )

        model.version += 1
        model.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "ok",
            "edit_id": str(edit_db.id),
            "version_before": version_before,
            "version_after": model.version,
        }
    finally:
        db.close()
