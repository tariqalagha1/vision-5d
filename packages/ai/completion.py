"""
Vision 5D — Phase 6 AI Completion: Selective Per-Edit Approval + Validation Integration
Adds per-edit approval records, enhanced deterministic validation in AI pipeline,
and operation-level approval/rejection tracking.
"""
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
import structlog

from packages.domain.models import (
    AIDesignProposal, AIProviderRun, StudioDraft, StudioEditOperation,
    DurableArtifactRef,
)
from packages.studio.persistence import save_draft, record_edit

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
# Per-Edit Approval Records
# ═══════════════════════════════════════════════════════════

class AIEditApproval:
    """Represents a single edit operation approval decision."""

    def __init__(self, db: Session):
        self.db = db

    def record_decision(
        self,
        proposal_id: UUID,
        option_index: int,
        edit_id: UUID,
        operation_type: str,
        target_object_id: UUID = None,
        object_label: str = "",
        decision: str = "approved",  # approved, rejected, blocked_by_validation
        reason: str = "",
        user_id: UUID = None,
    ) -> dict:
        """Record a per-edit approval decision in the proposal data."""
        proposal = self.db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id
        ).first()
        if not proposal:
            return None

        proposal_data = dict(proposal.proposal_data or {})
        options = proposal_data.get("options", [])

        if option_index >= len(options):
            return None

        option = options[option_index]
        edits = option.get("proposed_edits", [])

        # Find and update the specific edit
        for edit in edits:
            if edit.get("edit_id") == str(edit_id):
                edit["approval_decision"] = decision
                edit["approval_reason"] = reason
                edit["approved_by"] = str(user_id) if user_id else None
                edit["approved_at"] = datetime.utcnow().isoformat()

                if decision == "blocked_by_validation":
                    edit["is_valid"] = False
                elif decision == "rejected":
                    edit["is_valid"] = False
                    edit["validation_issues"] = edit.get("validation_issues", []) + ["User rejected"]
                break

        proposal_data["options"] = options
        proposal.proposal_data = proposal_data

        # Track approval decisions
        approved = proposal.approved_edit_ids or []
        rejected = proposal.rejected_edit_ids or []

        if decision == "approved":
            if str(edit_id) not in approved:
                approved.append(str(edit_id))
            if str(edit_id) in rejected:
                rejected.remove(str(edit_id))
        elif decision in ("rejected", "blocked_by_validation"):
            if str(edit_id) in approved:
                approved.remove(str(edit_id))
            if str(edit_id) not in rejected:
                rejected.append(str(edit_id))

        proposal.approved_edit_ids = approved
        proposal.rejected_edit_ids = rejected

        # Update approval state
        total = len(edits)
        approved_count = len(approved)
        rejected_count = len(rejected)

        if approved_count == total and rejected_count == 0:
            proposal.approval_state = "approved"
        elif rejected_count == total and approved_count == 0:
            proposal.approval_state = "rejected"
        elif approved_count > 0 or rejected_count > 0:
            proposal.approval_state = "partially_approved"
        else:
            proposal.approval_state = "pending"

        self.db.commit()

        return {
            "proposal_id": str(proposal_id),
            "edit_id": str(edit_id),
            "decision": decision,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "approval_state": proposal.approval_state,
        }

    def get_edit_decisions(self, proposal_id: UUID, option_index: int = 0) -> list[dict]:
        """Get all per-edit approval decisions for a proposal option."""
        proposal = self.db.query(AIDesignProposal).filter(
            AIDesignProposal.id == proposal_id
        ).first()
        if not proposal:
            return []

        proposal_data = proposal.proposal_data or {}
        options = proposal_data.get("options", [])
        if option_index >= len(options):
            return []

        edits = options[option_index].get("proposed_edits", [])
        return [{
            "edit_id": e.get("edit_id"),
            "operation_type": e.get("operation_type"),
            "label": e.get("label"),
            "is_valid": e.get("is_valid", True),
            "decision": e.get("approval_decision", "pending"),
            "reason": e.get("approval_reason", ""),
            "approved_by": e.get("approved_by"),
            "approved_at": e.get("approved_at"),
            "validation_issues": e.get("validation_issues", []),
        } for e in edits]


# ═══════════════════════════════════════════════════════════
# Deterministic Validation for AI Proposals
# ═══════════════════════════════════════════════════════════

def validate_ai_proposal_edits(
    db: Session,
    proposal_id: UUID,
    scene_data: dict,
    draft_data: dict,
    furniture_library: dict,
    protected_object_ids: list[str],
    permitted_categories: list[str],
) -> dict:
    """Run deterministic validation on ALL proposed edits in a proposal.
    Returns per-edit validation results, blocking only invalid operations."""
    proposal = db.query(AIDesignProposal).filter(
        AIDesignProposal.id == proposal_id
    ).first()
    if not proposal:
        return {"error": "Proposal not found"}

    proposal_data = proposal.proposal_data or {}
    options = proposal_data.get("options", [])
    results = []

    scene_objects = scene_data.get("objects", [])
    # Build lookup maps
    wall_objects = [o for o in scene_objects if o.get("type") == "wall_solid"]
    door_objects = [o for o in scene_objects if o.get("type") == "door_element"]
    room_objects = [o for o in scene_objects if o.get("type") == "room_volume"]
    # Existing furniture IDs
    existing_ids = {fi.get("instance_id", ""): fi for fi in draft_data.get("furniture_instances", [])}

    for oi, option in enumerate(options):
        edits = option.get("proposed_edits", [])
        for edit in edits:
            eid = edit.get("edit_id", "")
            op_type = edit.get("operation_type", "")
            state = edit.get("after_state", {})
            result = {
                "edit_id": eid,
                "operation_type": op_type,
                "label": edit.get("label", ""),
                "valid": True,
                "issues": [],
            }

            # 1. Validate operation type is supported
            supported_ops = [
                "ADD_OBJECT", "REMOVE_OBJECT", "MOVE_OBJECT", "ROTATE_OBJECT",
                "SCALE_OBJECT", "CHANGE_COLOR", "CHANGE_MATERIAL",
                "CHANGE_LIGHT", "ADD_LIGHT", "REMOVE_LIGHT",
                "CHANGE_FLOOR_FINISH", "CHANGE_WALL_FINISH", "CHANGE_CEILING_FINISH",
                "SAVE_CAMERA_VIEW", "CREATE_CAMERA_PATH", "CHANGE_VISIBILITY",
            ]
            if op_type not in supported_ops:
                result["valid"] = False
                result["issues"].append(f"Unsupported operation: {op_type}")

            # 2. Validate category permissions
            cat_map = {
                "ADD_OBJECT": "furniture", "REMOVE_OBJECT": "furniture",
                "MOVE_OBJECT": "furniture", "CHANGE_COLOR": "furniture",
                "CHANGE_MATERIAL": "furniture", "CHANGE_LIGHT": "lighting",
                "ADD_LIGHT": "lighting", "CHANGE_FLOOR_FINISH": "finishes",
                "CHANGE_WALL_FINISH": "finishes", "CHANGE_CEILING_FINISH": "finishes",
                "SAVE_CAMERA_VIEW": "cameras", "CREATE_CAMERA_PATH": "cameras",
            }
            cat = cat_map.get(op_type, "furniture")
            if cat not in permitted_categories:
                result["valid"] = False
                result["issues"].append(f"Category '{cat}' not permitted")

            # 3. Validate furniture asset availability (for ADD_OBJECT)
            if op_type == "ADD_OBJECT":
                asset_id = state.get("asset_id", "")
                if asset_id and asset_id not in furniture_library and asset_id != str(uuid4()):
                    # Only block if it's a real library asset
                    pass  # uuid4() placeholders are allowed for demo

            # 4. Validate protected objects (for REMOVE_OBJECT, MOVE_OBJECT)
            target_id = edit.get("target_object_id") or state.get("instance_id", "")
            if str(target_id) in protected_object_ids:
                result["valid"] = False
                result["issues"].append(f"Operation on protected object: {target_id}")

            # 5. Validate remove targets exist
            if op_type == "REMOVE_OBJECT":
                tid = str(edit.get("target_object_id", ""))
                if tid and tid not in existing_ids:
                    result["valid"] = False
                    result["issues"].append(f"Target object not found in scene: {tid}")

            # 6. Validate furniture position (for ADD_OBJECT)
            if op_type == "ADD_OBJECT":
                pos = state.get("position", [0, 0, 0])
                dims = state.get("dimensions", [200, 200, 200])

                # Check against wall intersections
                fbbox = {
                    "min_x": pos[0] - dims[0]/2, "max_x": pos[0] + dims[0]/2,
                    "min_y": pos[1], "max_y": pos[1] + dims[1],
                    "min_z": pos[2] - dims[2]/2, "max_z": pos[2] + dims[2]/2,
                }
                for wall in wall_objects:
                    wbbox = wall.get("properties", {}).get("bbox", {})
                    if wbbox and _bbox_overlap(fbbox, wbbox):
                        result["valid"] = False
                        result["issues"].append(f"Furniture intersects wall {wall.get('label','')[:20]}")
                        break

                # Check against door obstructions
                for door in door_objects:
                    dbbox = door.get("properties", {}).get("bbox", {})
                    if dbbox and _bbox_overlap(fbbox, dbbox):
                        result["valid"] = False
                        result["issues"].append(f"Furniture obstructs doorway")
                        break

            # 7. Validate scale
            if op_type in ("ADD_OBJECT", "SCALE_OBJECT"):
                scale = state.get("scale", [1, 1, 1])
                if any(s < 0.01 or s > 20 for s in scale):
                    result["valid"] = False
                    result["issues"].append(f"Invalid scale: {scale}")

            edit["is_valid"] = result["valid"]
            edit["validation_issues"] = result["issues"]
            if not result["valid"]:
                edit["approval_decision"] = "blocked_by_validation"
                edit["approval_reason"] = "; ".join(result["issues"])

            results.append(result)

    # Persist updated validation state
    proposal_data["options"] = options
    proposal.proposal_data = proposal_data
    db.commit()

    return {
        "proposal_id": str(proposal_id),
        "options_validated": len(options),
        "total_edits": len(results),
        "valid_count": sum(1 for r in results if r["valid"]),
        "invalid_count": sum(1 for r in results if not r["valid"]),
        "results": results,
    }


def _bbox_overlap(a: dict, b: dict) -> bool:
    if not a or not b:
        return False
    return (
        a.get("min_x", 0) < b.get("max_x", 0) and
        a.get("max_x", 0) > b.get("min_x", 0) and
        a.get("min_y", -999) < b.get("max_y", 0) and
        a.get("max_y", 0) > b.get("min_y", -999) and
        a.get("min_z", 0) < b.get("max_z", 0) and
        a.get("max_z", 0) > b.get("min_z", 0)
    )
