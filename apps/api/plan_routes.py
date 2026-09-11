"""
Vision 5D — Phase 2 API Routes (Async Durable Job Model)
Plan understanding endpoints now create durable jobs, not execute inline.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
import structlog, hashlib

from packages.domain.database import get_db
from packages.domain.models import DurableJob as DurableJobModel, UnderstandingGraph, GraphNode, GraphEdge
from packages.contracts.models import (
    JobState, JobSubmitResponse, DurableJob as DurableJobSchema,
    JobStatus, ProgressEvent,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2", tags=["Phase 2 — Plan Understanding"])


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    """Extract user_id and tenant_id from session (cookie or header)."""
    from apps.api.main import get_current_user
    return get_current_user(request)


def _submit_durable_job(
    db: Session, tenant_id: UUID, workspace_id: UUID, project_id: UUID,
    job_type: str, params: dict, idempotency_key: Optional[str] = None,
) -> DurableJobModel:
    """Create a durable job and submit it to the queue. Returns the persisted job."""
    from apps.api.main import get_current_tenant

    # Idempotency check
    if idempotency_key:
        existing = db.query(DurableJobModel).filter(
            DurableJobModel.idempotency_key == idempotency_key
        ).first()
        if existing:
            # Return existing job — don't create duplicate
            logger.info("idempotent_job_reuse", job_id=str(existing.id),
                        idempotency_key=idempotency_key, state=existing.state)
            return existing

    param_hash = hashlib.sha256(str(params).encode()).hexdigest()[:16]

    # Check for duplicate: same project + job_type + param_hash + not terminal
    duplicate = db.query(DurableJobModel).filter(
        DurableJobModel.project_id == project_id,
        DurableJobModel.tenant_id == tenant_id,
        DurableJobModel.job_type == job_type,
        DurableJobModel.param_hash == param_hash,
        ~DurableJobModel.state.in_([v.value for v in [
            JobState.COMPLETED, JobState.FAILED_TERMINAL, JobState.CANCELLED, JobState.EXPIRED
        ]])
    ).first()
    if duplicate:
        logger.info("duplicate_job_prevented", existing_job_id=str(duplicate.id),
                    job_type=job_type, state=duplicate.state)
        return duplicate

    # Check for completed duplicate — reuse result
    completed_duplicate = db.query(DurableJobModel).filter(
        DurableJobModel.project_id == project_id,
        DurableJobModel.tenant_id == tenant_id,
        DurableJobModel.job_type == job_type,
        DurableJobModel.param_hash == param_hash,
        DurableJobModel.state == JobState.COMPLETED.value,
    ).order_by(DurableJobModel.completed_at.desc()).first()
    if completed_duplicate:
        logger.info("completed_job_reuse", job_id=str(completed_duplicate.id),
                    job_type=job_type)
        return completed_duplicate

    key = idempotency_key or f"{tenant_id}:{project_id}:{job_type}:{param_hash}"

    job = DurableJobModel(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        job_type=job_type,
        idempotency_key=key,
        params=params,
        param_hash=param_hash,
        state=JobState.AUTHORIZED.value,
        initiated_by="user",
    )
    db.add(job)
    db.flush()

    # Transition: AUTHORIZED → QUEUED
    job.state = JobState.QUEUED.value
    db.commit()
    db.refresh(job)

    logger.info("durable_job_submitted", job_id=str(job.id), job_type=job_type,
                project_id=str(project_id), idempotency_key=key)

    return job


# ═══════════════════════════════════════════════════════════
# Async Pipeline Endpoints (Durable Job Model)
# ═══════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/understand", response_model=JobSubmitResponse)
async def understand_plan_async(
    project_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    manual_scale: Optional[str] = Form(None),
    workspace_id: Optional[UUID] = Form(None),
    db: Session = Depends(get_db),
):
    """D-PLAN-001: Submit plan understanding as a durable job.
    The API persists the job and returns immediately.
    The worker executes the pipeline independently.
    """
    user_id, tenant_id = _get_user_tenant(request)

    # Read uploaded file bytes
    try:
        image_bytes = await file.read()
    except Exception:
        raise HTTPException(400, "Cannot read uploaded file")

    # Store file bytes in params (production: upload first, reference by asset ID)
    content_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    idempotency_key = f"{tenant_id}:{project_id}:plan-understanding:{content_hash}"

    params = {
        "file_size": len(image_bytes),
        "content_hash": content_hash,
        "filename": file.filename,
        "manual_scale": manual_scale,
        "project_id": str(project_id),
    }

    ws_id = workspace_id or UUID("00000000-0000-0000-0000-00000000000a")

    job = _submit_durable_job(
        db=db, tenant_id=tenant_id, workspace_id=ws_id,
        project_id=project_id, job_type="plan-understanding",
        params=params, idempotency_key=idempotency_key,
    )

    # Save image bytes for worker (temp file)
    import tempfile, os as _os
    tmpdir = _os.path.join(_os.path.dirname(__file__), "..", "..", ".uploads")
    _os.makedirs(tmpdir, exist_ok=True)
    tmppath = _os.path.join(tmpdir, f"{job.id}.png")
    with open(tmppath, "wb") as f:
        f.write(image_bytes)

    return JobSubmitResponse(
        job_id=job.id,
        state=JobState(job.state),
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        status_endpoint=f"/api/v1/jobs/{job.id}",
    )


@router.get("/projects/{project_id}/jobs")
async def list_project_jobs(project_id: UUID, request: Request, db: Session = Depends(get_db)):
    """List active and recent jobs for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    jobs = db.query(DurableJobModel).filter(
        DurableJobModel.project_id == project_id,
        DurableJobModel.tenant_id == tenant_id,
    ).order_by(DurableJobModel.created_at.desc()).limit(20).all()

    return {
        "project_id": str(project_id),
        "jobs": [{
            "job_id": str(j.id),
            "job_type": j.job_type,
            "state": j.state,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        } for j in jobs],
    }


@router.get("/projects/{project_id}/latest-output")
async def latest_project_output(project_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Get the latest completed output versions for a project."""
    user_id, tenant_id = _get_user_tenant(request)

    last_graph = db.query(UnderstandingGraph).filter(
        UnderstandingGraph.project_id == project_id,
        UnderstandingGraph.tenant_id == tenant_id,
    ).order_by(UnderstandingGraph.version.desc()).first()

    from packages.domain.models import PersistedGeometry
    last_geom = db.query(PersistedGeometry).filter(
        PersistedGeometry.project_id == project_id,
        PersistedGeometry.tenant_id == tenant_id,
    ).order_by(PersistedGeometry.version.desc()).first()

    return {
        "project_id": str(project_id),
        "understanding": {
            "graph_id": str(last_graph.id) if last_graph else None,
            "version": last_graph.version if last_graph else None,
            "state": last_graph.state if last_graph else None,
        } if last_graph else None,
        "geometry": {
            "model_id": str(last_geom.id) if last_geom else None,
            "version": last_geom.version if last_geom else None,
            "state": last_geom.state if last_geom else None,
        } if last_geom else None,
    }
