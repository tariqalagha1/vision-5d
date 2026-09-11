"""
Vision 5D — Computer-Use API Routes
Authenticated endpoints for computer-use session management.
All computer control is gated behind authentication.
NVIDIA_API_KEY never leaves the server.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
import structlog

from packages.domain.database import get_db
from packages.computer_use.session import get_session_manager
from packages.computer_use.security import security_guard
from packages.computer_use import SecurityConfig, SessionState

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/computer-use", tags=["Computer Use"])

def _get_cu_manager():
    return get_session_manager()


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    from apps.api.main import get_current_user
    return get_current_user(request)


# ═══════════════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════════════

@router.post("/sessions")
async def create_session(request: Request, db: Session = Depends(get_db)):
    """Create a new computer-use session."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json() if hasattr(request, 'json') else {}
    objective = body.get("objective", "") if isinstance(body, dict) else ""

    # Enable security for computer use
    security_guard.config.enabled = True

    session = _get_cu_manager().create_session(objective=objective)
    return {
        "session_id": str(session.session_id),
        "state": session.state.value,
        "objective": objective,
        "max_actions": session.max_actions,
        "security_enabled": security_guard.config.enabled,
    }


@router.get("/sessions")
async def list_sessions(request: Request, db: Session = Depends(get_db)):
    """List all computer-use sessions."""
    user_id, tenant_id = _get_user_tenant(request)
    return {"sessions": _get_cu_manager().list_sessions()}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Get session status including current screenshot, last analysis, and action history."""
    user_id, tenant_id = _get_user_tenant(request)
    status = _get_cu_manager().get_session_status(session_id)
    if "error" in status:
        raise HTTPException(404, status["error"])
    return status


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Start the computer-use loop."""
    user_id, tenant_id = _get_user_tenant(request)
    result = _get_cu_manager().start_session(session_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    user_id, tenant_id = _get_user_tenant(request)
    return _get_cu_manager().pause_session(session_id)


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    user_id, tenant_id = _get_user_tenant(request)
    return _get_cu_manager().resume_session(session_id)


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    user_id, tenant_id = _get_user_tenant(request)
    return _get_cu_manager().stop_session(session_id)


@router.post("/sessions/{session_id}/emergency-stop")
async def emergency_stop(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Emergency stop — immediately halts all actions."""
    user_id, tenant_id = _get_user_tenant(request)
    return _get_cu_manager().emergency_stop(session_id)


# ═══════════════════════════════════════════════════════════
# Action Execution
# ═══════════════════════════════════════════════════════════

@router.post("/sessions/{session_id}/step")
async def execute_step(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Execute one step of the computer-use loop (capture → analyze → validate → execute → verify)."""
    user_id, tenant_id = _get_user_tenant(request)
    result = _get_cu_manager().execute_step(session_id)
    if "error" in result and result.get("step") in ("capture", "validate"):
        raise HTTPException(400, result["error"])
    return result


@router.post("/sessions/{session_id}/approve")
async def approve_confirmation(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Approve a pending confirmation and execute the action."""
    user_id, tenant_id = _get_user_tenant(request)
    result = _get_cu_manager().approve_confirmation(session_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/sessions/{session_id}/reject")
async def reject_confirmation(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Reject a pending confirmation."""
    user_id, tenant_id = _get_user_tenant(request)
    return _get_cu_manager().reject_confirmation(session_id)


# ═══════════════════════════════════════════════════════════
# Screenshots & Evidence
# ═══════════════════════════════════════════════════════════

@router.get("/sessions/{session_id}/screenshots/{filename}")
async def get_screenshot(session_id: str, filename: str, request: Request, db: Session = Depends(get_db)):
    """Retrieve a screenshot from a session (authenticated)."""
    user_id, tenant_id = _get_user_tenant(request)
    import os
    from fastapi.responses import FileResponse

    evidence_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "evidence",
        "V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001", "computer_use", "screenshots"
    )
    path = os.path.normpath(os.path.join(evidence_dir, filename))
    if ".." in path or not os.path.exists(path):
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path, media_type="image/png")


@router.get("/sessions/{session_id}/audit")
async def get_audit_log(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Get the audit log for a session."""
    user_id, tenant_id = _get_user_tenant(request)
    return {"audit_log": security_guard.get_audit_log(session_id)}


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@router.get("/config")
async def get_config(request: Request, db: Session = Depends(get_db)):
    """Get computer-use configuration (no secrets)."""
    user_id, tenant_id = _get_user_tenant(request)
    cfg = security_guard.config
    return {
        "enabled": cfg.enabled,
        "domain_allowlist": cfg.domain_allowlist,
        "app_allowlist": cfg.app_allowlist,
        "max_actions_per_session": cfg.max_actions_per_session,
        "action_timeout_seconds": cfg.action_timeout_seconds,
        "audit_enabled": cfg.audit_enabled,
        "require_confirmation_for": [r.value for r in cfg.require_confirmation_for],
        "emergency_stop_active": security_guard.is_emergency_stopped,
    }


@router.put("/config")
async def update_config(request: Request, db: Session = Depends(get_db)):
    """Update computer-use security configuration."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json() if hasattr(request, 'json') else {}

    if isinstance(body, dict):
        if "enabled" in body:
            security_guard.config.enabled = bool(body["enabled"])
        if "domain_allowlist" in body:
            security_guard.config.domain_allowlist = body["domain_allowlist"]
        if "max_actions_per_session" in body:
            security_guard.config.max_actions_per_session = int(body["max_actions_per_session"])

    return {"status": "updated", "config": {
        "enabled": security_guard.config.enabled,
        "domain_allowlist": security_guard.config.domain_allowlist,
        "max_actions_per_session": security_guard.config.max_actions_per_session,
    }}
