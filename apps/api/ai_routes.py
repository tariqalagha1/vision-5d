"""
Vision 5D — Phase 6 AI Intelligence API Routes
AI analysis, proposal generation, approval, branching, and audit trail.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from typing import Optional
import structlog, json as _json, hashlib
from datetime import datetime

from packages.domain.database import get_db, SessionLocal
from packages.domain.models import (
    Scene3DVersion, StudioDraft, StudioSceneVersion, StudioEditOperation,
    DurableJob as DurableJobModel, AIDesignProposal, AIProviderRun, AIUsageRecord,
)
from packages.contracts.models import JobState, JobSubmitResponse
from packages.studio.persistence import (
    load_draft, save_draft, commit_version, record_edit,
)
from packages.ai.analysis import scene_analyzer
from packages.ai.proposal import proposal_generator
from packages.ai.contracts import AIApprovalRequest, AIRequestSubmit, AIApprovalState

router = APIRouter(prefix="/api/v6/ai", tags=["Phase 6 — AI Intelligence"])
logger = structlog.get_logger()


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    from apps.api.main import get_current_user
    return get_current_user(request)


def _submit_durable_job(db, tenant_id, workspace_id, project_id, job_type, params, key=None):
    key = key or f"{tenant_id}:{project_id}:{job_type}:{hashlib.sha256(str(params).encode()).hexdigest()[:16]}"
    existing = db.query(DurableJobModel).filter(DurableJobModel.idempotency_key == key).first()
    if existing:
        return existing
    job = DurableJobModel(
        tenant_id=tenant_id, workspace_id=workspace_id, project_id=project_id,
        job_type=job_type, idempotency_key=key, params=params,
        param_hash=hashlib.sha256(str(params).encode()).hexdigest()[:16],
        state=JobState.AUTHORIZED.value, initiated_by="user",
    )
    db.add(job); db.flush()
    job.state = JobState.QUEUED.value
    db.commit(); db.refresh(job)
    return job


# ═══════════════════════════════════════════════════════════
# AI Design Request
# ═══════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/design")
async def ai_design_request(project_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Submit an AI design request as a durable job. Returns immediately."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()

    # Find source scene and studio version
    scene = db.query(Scene3DVersion).filter(
        Scene3DVersion.project_id == project_id, Scene3DVersion.tenant_id == tenant_id
    ).order_by(Scene3DVersion.version.desc()).first()

    studio_ver = None
    if body.get("source_studio_version"):
        studio_ver = db.query(StudioSceneVersion).filter(
            StudioSceneVersion.id == UUID(body["source_studio_version"]),
            StudioSceneVersion.tenant_id == tenant_id,
        ).first()

    params = {
        "project_id": str(project_id),
        "user_text": body.get("user_text", ""),
        "objective": body.get("objective", "custom"),
        "target_room_ids": body.get("target_room_ids", []),
        "permitted_categories": body.get("permitted_categories", ["furniture", "finishes", "lighting", "cameras"]),
        "protected_object_ids": body.get("protected_object_ids", []),
        "budget_band": body.get("budget_band", "unspecified"),
        "seating_capacity": body.get("seating_capacity"),
        "style_preference": body.get("style_preference", ""),
        "source_scene_id": str(scene.id) if scene else None,
        "source_scene_version": scene.version if scene else 1,
        "source_studio_version": str(studio_ver.id) if studio_ver else None,
    }

    ws_id = UUID("00000000-0000-0000-0000-00000000000a")
    job = _submit_durable_job(db, tenant_id, ws_id, project_id, "ai-design-proposal", params)
    return JobSubmitResponse(
        job_id=job.id, state=JobState(job.state),
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        status_endpoint=f"/api/v1/jobs/{job.id}",
    )


# ═══════════════════════════════════════════════════════════
# Proposal Retrieval
# ═══════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/proposals")
async def list_proposals(project_id: UUID, request: Request):
    """List AI proposals for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        # Verify project belongs to tenant
        from packages.domain.models import Project
        proj = db.query(Project).filter(
            Project.id == project_id, Project.tenant_id == tenant_id
        ).first()
        if not proj:
            raise HTTPException(404, "Project not found")

        proposals = db.query(AIDesignProposal).filter(
            AIDesignProposal.project_id == project_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).order_by(AIDesignProposal.created_at.desc()).limit(20).all()

        return {
            "project_id": str(project_id),
            "proposals": [{
                "proposal_id": str(p.id),
                "objective": p.objective,
                "user_text": p.user_text,
                "provider": p.provider,
                "approval_state": p.approval_state,
                "option_count": len((p.proposal_data or {}).get("options", [])),
                "input_tokens": p.input_tokens,
                "output_tokens": p.output_tokens,
                "has_branch": p.ai_branch_draft_id is not None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            } for p in proposals],
        }
    finally:
        db.close()


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: UUID, request: Request):
    """Get a specific AI proposal with full details."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        p = db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).first()
        if not p:
            raise HTTPException(404, "Proposal not found")

        return {
            "proposal_id": str(p.id),
            "objective": p.objective,
            "user_text": p.user_text,
            "provider": p.provider,
            "model": p.model,
            "approval_state": p.approval_state,
            "approved_option_index": p.approved_option_index,
            "approved_edit_ids": p.approved_edit_ids,
            "rejected_edit_ids": p.rejected_edit_ids,
            "has_branch": p.ai_branch_draft_id is not None,
            "ai_branch_draft_id": str(p.ai_branch_draft_id) if p.ai_branch_draft_id else None,
            "ai_branch_version_id": str(p.ai_branch_version_id) if p.ai_branch_version_id else None,
            "proposal_data": p.proposal_data,
            "input_tokens": p.input_tokens,
            "output_tokens": p.output_tokens,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Proposal Approval
# ═══════════════════════════════════════════════════════════

@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: UUID, request: Request):
    """Approve AI proposal edits and create an AI branch draft."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        p = db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).first()
        if not p:
            raise HTTPException(404, "Proposal not found")

        approved_ids = [UUID(aid) for aid in body.get("approved_edit_ids", [])]
        rejected_ids = [UUID(rid) for rid in body.get("rejected_edit_ids", [])]
        option_idx = body.get("option_index", 0)

        p.approved_edit_ids = [str(aid) for aid in approved_ids]
        p.rejected_edit_ids = [str(rid) for rid in rejected_ids]
        p.approved_option_index = option_idx
        p.approval_state = "partially_approved" if rejected_ids else "approved"

        # Get source draft for branching
        draft_data = load_draft(db, p.project_id, tenant_id)
        if not draft_data:
            # Create a new draft from scene data
            scene = db.query(Scene3DVersion).filter(
                Scene3DVersion.id == p.source_scene_id
            ).first()
            source_draft = {"draft_data": {}}
        else:
            source_draft = draft_data

        # Create AI branch draft
        options = (p.proposal_data or {}).get("options", [])
        option = options[option_idx] if option_idx < len(options) else None

        if option:
            ai_draft_data = dict(source_draft.get("draft_data", {}))
            # Apply approved edits
            furniture = list(ai_draft_data.get("furniture_instances", []))
            for edit in option.get("proposed_edits", []):
                eid = UUID(edit.get("edit_id", str(uuid4())))
                if eid in approved_ids:
                    if edit.get("operation_type") == "ADD_OBJECT":
                        state = edit.get("after_state", {})
                        furniture.append({
                            "instance_id": str(uuid4()),
                            "asset_id": state.get("asset_id", str(uuid4())),
                            "label": state.get("label", edit.get("label", "AI Object")),
                            "position": state.get("position", [0, 0, 0]),
                            "rotation": state.get("rotation", [0, 0, 0]),
                            "scale": state.get("scale", [1, 1, 1]),
                            "color_override": state.get("color_override"),
                            "dimensions": state.get("dimensions", [200, 200, 200]),
                            "visible": True,
                            "locked": False,
                        })
                    elif edit.get("operation_type") == "REMOVE_OBJECT":
                        fid = edit.get("target_object_id")
                        furniture = [f for f in furniture if f.get("instance_id") != str(fid)]
                    elif edit.get("operation_type") in ("CHANGE_FLOOR_FINISH", "CHANGE_WALL_FINISH"):
                        ai_draft_data["finishes"] = {**ai_draft_data.get("finishes", {}), **edit.get("after_state", {})}
                    elif edit.get("operation_type") == "CHANGE_LIGHT":
                        ai_draft_data["lights"] = {**ai_draft_data.get("lights", {}), **edit.get("after_state", {})}

            ai_draft_data["furniture_instances"] = furniture
            ai_draft_data["_ai_proposal_id"] = str(proposal_id)

            # Persist AI branch
            from packages.studio.persistence import save_draft as studio_save_draft
            branch = studio_save_draft(
                db, p.project_id, tenant_id,
                p.source_scene_id or UUID("00000000-0000-0000-0000-00000000000a"),
                p.source_studio_version or 1,
                ai_draft_data,
            )
            p.ai_branch_draft_id = branch.id

        db.commit()

        return {
            "proposal_id": str(proposal_id),
            "approval_state": p.approval_state,
            "approved_count": len(approved_ids),
            "rejected_count": len(rejected_ids),
            "ai_branch_draft_id": str(p.ai_branch_draft_id) if p.ai_branch_draft_id else None,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Usage Records
# ═══════════════════════════════════════════════════════════

@router.get("/usage/{project_id}")
async def ai_usage(project_id: UUID, request: Request):
    """Get AI usage records for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        records = db.query(AIUsageRecord).filter(
            AIUsageRecord.project_id == project_id,
            AIUsageRecord.tenant_id == tenant_id,
        ).order_by(AIUsageRecord.created_at.desc()).limit(50).all()

        total_cost = sum(r.estimated_cost or 0 for r in records)
        total_input = sum(r.input_tokens or 0 for r in records)
        total_output = sum(r.output_tokens or 0 for r in records)

        return {
            "project_id": str(project_id),
            "records": [{
                "provider": r.provider, "model": r.model,
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "estimated_cost": r.estimated_cost,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            } for r in records],
            "total_cost": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Per-Edit Approval + Validation Integration
# ═══════════════════════════════════════════════════════════

@router.post("/proposals/{proposal_id}/validate")
async def validate_proposal_edits(proposal_id: UUID, request: Request):
    """Run full deterministic validation on all proposed edits."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.ai.completion import validate_ai_proposal_edits
        from packages.domain.models import FurnitureLibraryItem

        proposal = db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).first()
        if not proposal:
            raise HTTPException(404, "Proposal not found")

        # Load scene
        scene = db.query(Scene3DVersion).filter(
            Scene3DVersion.id == proposal.source_scene_id
        ).first()
        scene_data = scene.scene_data if scene else {}

        # Load draft for existing furniture
        draft = db.query(StudioDraft).filter(
            StudioDraft.project_id == proposal.project_id
        ).first()
        draft_data = draft.draft_data if draft else {}

        # Furniture library
        lib = {str(i.id): i.name for i in db.query(FurnitureLibraryItem).filter(
            FurnitureLibraryItem.is_global == True).all()}

        # Get protected objects from proposal data
        pd = proposal.proposal_data or {}
        protected = pd.get("protected_object_ids", [])

        result = validate_ai_proposal_edits(
            db, proposal_id, scene_data, draft_data, lib, protected,
            pd.get("permitted_categories", ["furniture", "finishes", "lighting", "cameras"]),
        )
        return result
    finally:
        db.close()


@router.post("/proposals/{proposal_id}/approve-edit")
async def approve_single_edit(proposal_id: UUID, request: Request):
    """Approve or reject a single edit operation within a proposal."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        from packages.ai.completion import AIEditApproval

        proposal = db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).first()
        if not proposal:
            raise HTTPException(404, "Proposal not found")

        approver = AIEditApproval(db)
        result = approver.record_decision(
            proposal_id=proposal_id,
            option_index=body.get("option_index", 0),
            edit_id=UUID(body["edit_id"]),
            operation_type=body.get("operation_type", ""),
            target_object_id=UUID(body.get("target_object_id")) if body.get("target_object_id") else None,
            object_label=body.get("object_label", ""),
            decision=body.get("decision", "approved"),
            reason=body.get("reason", ""),
            user_id=user_id,
        )
        return result
    finally:
        db.close()


@router.get("/proposals/{proposal_id}/edit-decisions")
async def get_edit_decisions(proposal_id: UUID, request: Request, option_index: int = 0):
    """Get per-edit approval decisions for a proposal option."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.ai.completion import AIEditApproval

        proposal = db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id,
            AIDesignProposal.tenant_id == tenant_id,
        ).first()
        if not proposal:
            raise HTTPException(404, "Proposal not found")

        approver = AIEditApproval(db)
        decisions = approver.get_edit_decisions(proposal_id, option_index)
        return {
            "proposal_id": str(proposal_id),
            "option_index": option_index,
            "approval_state": proposal.approval_state,
            "decisions": decisions,
            "approved_count": len(proposal.approved_edit_ids or []),
            "rejected_count": len(proposal.rejected_edit_ids or []),
        }
    finally:
        db.close()
