"""
Vision 5D — Phase 5 Studio Persistence
Draft save/load, edit operations, undo/redo, version management, furniture library.
"""
import json as _json, structlog
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from packages.domain.models import (
    StudioDraft, StudioSceneVersion, StudioEditOperation, FurnitureLibraryItem,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
# Draft Management
# ═══════════════════════════════════════════════════════════

def load_draft(db: Session, project_id: UUID, tenant_id: UUID) -> dict:
    """Load the active studio draft for a project, or return None."""
    draft = db.query(StudioDraft).filter(
        StudioDraft.project_id == project_id,
        StudioDraft.tenant_id == tenant_id,
    ).order_by(StudioDraft.updated_at.desc()).first()
    if not draft:
        return None
    return {
        "draft_id": str(draft.id),
        "draft_data": draft.draft_data or {},
        "save_counter": draft.save_counter,
        "source_scene_id": str(draft.source_scene_id) if draft.source_scene_id else None,
        "source_scene_version": draft.source_scene_version,
        "state": draft.state,
    }


def save_draft(db: Session, project_id: UUID, tenant_id: UUID, source_scene_id: UUID,
               source_scene_version: int, draft_data: dict) -> StudioDraft:
    """Save or update studio draft state."""
    draft = db.query(StudioDraft).filter(
        StudioDraft.project_id == project_id,
        StudioDraft.tenant_id == tenant_id,
    ).first()

    if draft:
        draft.draft_data = draft_data
        draft.save_counter = (draft.save_counter or 0) + 1
        draft.updated_at = datetime.utcnow()
    else:
        draft = StudioDraft(
            tenant_id=tenant_id, project_id=project_id,
            source_scene_id=source_scene_id,
            source_scene_version=source_scene_version,
            draft_data=draft_data, save_counter=1,
        )
        db.add(draft)

    db.commit()
    db.refresh(draft)
    return draft


# ═══════════════════════════════════════════════════════════
# Edit Operations
# ═══════════════════════════════════════════════════════════

def record_edit(db: Session, draft_id: UUID, operation: dict) -> StudioEditOperation:
    """Record a single edit operation for undo/redo support."""
    draft = db.query(StudioDraft).filter(StudioDraft.id == draft_id).first()
    seq = db.query(StudioEditOperation).filter(
        StudioEditOperation.draft_id == draft_id
    ).count()

    op = StudioEditOperation(
        draft_id=draft_id,
        user_id=UUID(operation.get("user_id", str(uuid4()))),
        target_object_id=UUID(operation["target_object_id"]) if operation.get("target_object_id") else None,
        object_type=operation.get("object_type", ""),
        operation_type=operation["operation_type"],
        before_state=operation.get("before_state", {}),
        after_state=operation.get("after_state", {}),
        sequence=seq + 1,
    )
    db.add(op)
    db.commit()
    return op


def batch_record_edits(db: Session, draft_id: UUID, operations: list[dict]) -> list[StudioEditOperation]:
    """Record multiple edit operations in a batch."""
    results = []
    for op_data in operations:
        results.append(record_edit(db, draft_id, op_data))
    return results


def get_edit_history(db: Session, draft_id: UUID, limit: int = 200) -> list[dict]:
    """Get edit operation history for a draft."""
    ops = db.query(StudioEditOperation).filter(
        StudioEditOperation.draft_id == draft_id,
        StudioEditOperation.is_undone == False,
    ).order_by(StudioEditOperation.sequence.desc()).limit(limit).all()
    return [{
        "operation_id": str(o.id),
        "operation_type": o.operation_type,
        "target_object_id": str(o.target_object_id) if o.target_object_id else None,
        "sequence": o.sequence,
        "before_state": o.before_state,
        "after_state": o.after_state,
        "timestamp": o.timestamp.isoformat() if o.timestamp else None,
    } for o in reversed(ops)]


def mark_undone(db: Session, operation_id: UUID) -> bool:
    """Mark an edit operation as undone."""
    op = db.query(StudioEditOperation).filter(StudioEditOperation.id == operation_id).first()
    if op:
        op.is_undone = True
        db.commit()
        return True
    return False


# ═══════════════════════════════════════════════════════════
# Version Management
# ═══════════════════════════════════════════════════════════

def commit_version(db: Session, draft_id: UUID, name: str, description: str,
                   user_id: UUID = None) -> StudioSceneVersion:
    """Commit the current draft as a named studio version."""
    draft = db.query(StudioDraft).filter(StudioDraft.id == draft_id).first()
    if not draft:
        raise ValueError("Draft not found")

    existing = db.query(StudioSceneVersion).filter(
        StudioSceneVersion.project_id == draft.project_id,
        StudioSceneVersion.tenant_id == draft.tenant_id,
    ).order_by(StudioSceneVersion.version_number.desc()).first()
    version_num = (existing.version_number + 1) if existing else 1

    version = StudioSceneVersion(
        tenant_id=draft.tenant_id, project_id=draft.project_id,
        source_scene_id=draft.source_scene_id,
        source_scene_version=draft.source_scene_version,
        version_number=version_num, name=name, description=description,
        state="COMMITTED",
        draft_snapshot=draft.draft_data or {},
        edit_count=draft.save_counter or 0,
        lineage=f"scene_v{draft.source_scene_version} → studio_v{version_num}",
        created_by=user_id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    logger.info("studio_version_committed", version_id=str(version.id),
                version_number=version_num, name=name)
    return version


def list_versions(db: Session, project_id: UUID, tenant_id: UUID) -> list[StudioSceneVersion]:
    """List all studio versions for a project."""
    return db.query(StudioSceneVersion).filter(
        StudioSceneVersion.project_id == project_id,
        StudioSceneVersion.tenant_id == tenant_id,
    ).order_by(StudioSceneVersion.version_number.desc()).all()


def load_version(db: Session, version_id: UUID) -> dict:
    """Load a specific studio version's snapshot."""
    v = db.query(StudioSceneVersion).filter(StudioSceneVersion.id == version_id).first()
    if not v:
        return None
    return {
        "version_id": str(v.id),
        "version_number": v.version_number,
        "name": v.name,
        "description": v.description,
        "state": v.state,
        "edit_count": v.edit_count,
        "draft_snapshot": v.draft_snapshot,
        "lineage": v.lineage,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


# ═══════════════════════════════════════════════════════════
# Furniture Library
# ═══════════════════════════════════════════════════════════

def seed_furniture_library(db: Session):
    """Seed the furniture library with default items."""
    existing = db.query(FurnitureLibraryItem).count()
    if existing > 0:
        return existing

    items = [
        ("Sofa 3-Seater", "living_room", "seating", 2200, 850, 900),
        ("Armchair", "living_room", "seating", 900, 900, 850),
        ("Coffee Table", "living_room", "tables", 1200, 450, 600),
        ("Dining Table", "dining", "tables", 1800, 750, 900),
        ("Dining Chair", "dining", "seating", 500, 850, 500),
        ("Bed Queen", "bedroom", "beds", 1600, 1200, 2100),
        ("Bedside Table", "bedroom", "storage", 500, 500, 400),
        ("Wardrobe", "bedroom", "storage", 1200, 2200, 600),
        ("Office Desk", "office", "tables", 1400, 750, 700),
        ("Office Chair", "office", "seating", 600, 1100, 600),
        ("Bookshelf", "office", "storage", 900, 2000, 350),
        ("Kitchen Counter", "kitchen", "surfaces", 3000, 900, 600),
        ("Bar Stool", "kitchen", "seating", 450, 750, 450),
        ("Bathroom Vanity", "bathroom", "sanitary", 900, 850, 500),
        ("Toilet", "bathroom", "sanitary", 400, 450, 650),
        ("TV Stand", "living_room", "storage", 1500, 500, 400),
        ("Floor Lamp", "lighting", "lighting", 400, 1800, 400),
        ("Rug Large", "living_room", "decoration", 2000, 10, 3000),
        ("Plant Large", "decoration", "decoration", 500, 1500, 500),
        ("Shoe Rack", "bedroom", "storage", 800, 1200, 350),
    ]

    for name, cat, subcat, w, h, d in items:
        db.add(FurnitureLibraryItem(
            name=name, category=cat, subcategory=subcat,
            dimensions_w=w, dimensions_h=h, dimensions_d=d,
            is_global=True,
        ))
    db.commit()
    logger.info("furniture_library_seeded", count=len(items))
    return len(items)


def list_furniture(db: Session, category: str = None) -> list[dict]:
    """List furniture library items."""
    q = db.query(FurnitureLibraryItem).filter(FurnitureLibraryItem.is_global == True)
    if category:
        q = q.filter(FurnitureLibraryItem.category == category)
    items = q.all()
    return [{
        "asset_id": str(i.id),
        "name": i.name,
        "category": i.category,
        "subcategory": i.subcategory,
        "dimensions": (i.dimensions_w, i.dimensions_h, i.dimensions_d),
        "thumbnail": i.thumbnail,
    } for i in items]
