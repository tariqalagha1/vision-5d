"""
Vision 5D — Phase 5 Studio API Routes
Draft management, edit operations, furniture, materials, lights, cameras, versions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from typing import Optional
import structlog, json as _json

from packages.domain.database import get_db, SessionLocal
from packages.domain.models import Scene3DVersion, StudioDraft, StudioSceneVersion, StudioEditOperation
from packages.studio.persistence import (
    load_draft, save_draft, record_edit, batch_record_edits,
    get_edit_history, mark_undone, commit_version, list_versions, load_version,
    seed_furniture_library, list_furniture,
)

router = APIRouter(prefix="/api/v5/studio", tags=["Phase 5 — Studio"])
logger = structlog.get_logger()


def _get_user_tenant(request: Request) -> tuple[UUID, UUID]:
    from apps.api.main import get_current_user
    return get_current_user(request)


# ═══════════════════════════════════════════════════════════
# Draft Management
# ═══════════════════════════════════════════════════════════

@router.get("/draft/{project_id}")
async def get_draft(project_id: UUID, request: Request):
    """Load the active studio draft for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        draft_data = load_draft(db, project_id, tenant_id)

        # Get source scene info
        scene = None
        if draft_data and draft_data.get("source_scene_id"):
            scene = db.query(Scene3DVersion).filter(
                Scene3DVersion.id == UUID(draft_data["source_scene_id"])
            ).first()

        result = {
            "draft": draft_data,
            "has_draft": draft_data is not None,
            "source_scene": {
                "scene_id": str(scene.id) if scene else None,
                "version": scene.version if scene else None,
                "state": scene.state if scene else None,
                "lineage": scene.lineage if scene else None,
            } if scene else None,
        }
        return result
    finally:
        db.close()


@router.post("/draft/{project_id}")
async def save_draft_endpoint(project_id: UUID, request: Request):
    """Save the studio draft state."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        source_scene_id = UUID(body.get("source_scene_id", str(uuid4())))
        source_scene_version = body.get("source_scene_version", 1)
        draft_data = body.get("draft_data", {})

        draft = save_draft(db, project_id, tenant_id, source_scene_id,
                          source_scene_version, draft_data)
        return {
            "draft_id": str(draft.id),
            "save_counter": draft.save_counter,
            "state": draft.state,
            "saved": True,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Edit Operations
# ═══════════════════════════════════════════════════════════

@router.post("/draft/{project_id}/edits")
async def apply_edits(project_id: UUID, request: Request):
    """Apply one or more edit operations and persist them."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        # Ensure draft exists
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            raise HTTPException(404, "No draft found. Create a draft first.")

        draft_id = UUID(draft_data["draft_id"])
        operations = body.get("operations", [])

        recorded = []
        for op in operations:
            op["user_id"] = str(user_id)
            rec = record_edit(db, draft_id, op)
            recorded.append({
                "operation_id": str(rec.id),
                "sequence": rec.sequence,
                "operation_type": rec.operation_type,
            })

        return {
            "recorded": len(recorded),
            "operations": recorded,
            "draft_id": str(draft_id),
        }
    finally:
        db.close()


@router.post("/draft/{project_id}/undo")
async def undo_operation(project_id: UUID, request: Request):
    """Undo the last edit operation."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        body = await request.json() if await request.body() else {}
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            raise HTTPException(404, "No draft found")

        draft_id = UUID(draft_data["draft_id"])
        # Find the last non-undone operation
        last_op = db.query(StudioEditOperation).filter(
            StudioEditOperation.draft_id == draft_id,
            StudioEditOperation.is_undone == False,
        ).order_by(StudioEditOperation.sequence.desc()).first()

        if not last_op:
            return {"undone": False, "message": "Nothing to undo"}

        if body.get("operation_id"):
            target = db.query(StudioEditOperation).filter(
                StudioEditOperation.id == UUID(body["operation_id"])
            ).first()
            if target:
                target.is_undone = True
        else:
            last_op.is_undone = True
        db.commit()

        return {
            "undone": True,
            "operation_id": str(last_op.id),
            "operation_type": last_op.operation_type,
            "before_state": last_op.before_state,
        }
    finally:
        db.close()


@router.get("/draft/{project_id}/history")
async def edit_history(project_id: UUID, request: Request):
    """Get edit operation history."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            return {"history": [], "count": 0}

        draft_id = UUID(draft_data["draft_id"])
        history = get_edit_history(db, draft_id)
        return {"history": history, "count": len(history)}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Furniture Library
# ═══════════════════════════════════════════════════════════

@router.get("/furniture")
async def furniture_library(request: Request, category: str = None):
    """List available furniture items."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        seed_furniture_library(db)
        items = list_furniture(db, category)
        categories = sorted(set(i["category"] for i in items))
        return {
            "items": items,
            "categories": categories,
            "total": len(items),
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Version Management
# ═══════════════════════════════════════════════════════════

@router.post("/draft/{project_id}/commit")
async def commit_studio_version(project_id: UUID, request: Request):
    """Commit the current draft as a named Studio Version."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            raise HTTPException(404, "No draft to commit")

        draft_id = UUID(draft_data["draft_id"])
        version = commit_version(
            db, draft_id,
            name=body.get("name", f"Version {draft_data.get('save_counter', 0)}"),
            description=body.get("description", ""),
            user_id=user_id,
        )

        return {
            "version_id": str(version.id),
            "version_number": version.version_number,
            "name": version.name,
            "lineage": version.lineage,
            "committed": True,
        }
    finally:
        db.close()


@router.get("/versions/{project_id}")
async def studio_versions(project_id: UUID, request: Request):
    """List studio versions for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        versions = list_versions(db, project_id, tenant_id)
        return {
            "project_id": str(project_id),
            "versions": [{
                "version_id": str(v.id),
                "version_number": v.version_number,
                "name": v.name,
                "description": v.description,
                "state": v.state,
                "edit_count": v.edit_count,
                "lineage": v.lineage,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            } for v in versions],
        }
    finally:
        db.close()


@router.get("/version/{version_id}")
async def get_studio_version(version_id: UUID, request: Request):
    """Load a specific studio version."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        v = load_version(db, version_id)
        if not v:
            raise HTTPException(404, "Version not found")
        return v
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Durable Undo/Redo
# ═══════════════════════════════════════════════════════════

@router.post("/draft/{project_id}/redo")
async def redo_operation(project_id: UUID, request: Request):
    """Redo the last undone operation."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            raise HTTPException(404, "No draft found")

        draft_id = UUID(draft_data["draft_id"])
        last_undone = db.query(StudioEditOperation).filter(
            StudioEditOperation.draft_id == draft_id,
            StudioEditOperation.is_undone == True,
        ).order_by(StudioEditOperation.sequence.desc()).first()

        if not last_undone:
            return {"redone": False, "message": "Nothing to redo"}

        last_undone.is_undone = False
        db.commit()

        return {
            "redone": True,
            "operation_id": str(last_undone.id),
            "operation_type": last_undone.operation_type,
            "after_state": last_undone.after_state,
            "sequence": last_undone.sequence,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Studio-Aware Export
# ═══════════════════════════════════════════════════════════

@router.get("/versions/{project_id}/{version_id}/export/glb")
async def export_studio_version_glb(project_id: UUID, version_id: UUID, request: Request):
    """Export a committed Studio Version as GLB with furniture, colors, and finishes."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.studio.studio_export import export_studio_glb, generate_studio_manifest
        from packages.scene3d.glb_export import validate_glb
        from packages.domain.models import DurableArtifactRef

        # Load studio version
        v = load_version(db, version_id)
        if not v:
            raise HTTPException(404, "Studio version not found")

        # Load source scene data
        scene_id_str = v.get("draft_snapshot", {}).get("source_scene_id") or (
            db.query(StudioDraft).filter(StudioDraft.id == UUID(v.get("version_id", str(uuid4())))).first()
        )
        scene_db = db.query(Scene3DVersion).filter(
            Scene3DVersion.project_id == project_id,
            Scene3DVersion.tenant_id == tenant_id,
        ).order_by(Scene3DVersion.version.desc()).first()

        scene_data = scene_db.scene_data if scene_db else {}

        # Generate Studio GLB
        studio_draft = v.get("draft_snapshot", {})
        glb_bytes = export_studio_glb(scene_data, studio_draft)
        validation = validate_glb(glb_bytes)
        content_hash = validation.get("sha256", hashlib.sha256(glb_bytes).hexdigest())

        # Persist artifact reference
        dart = DurableArtifactRef(
            tenant_id=tenant_id, project_id=project_id,
            job_id=uuid4(), artifact_type="studio-export-glb",
            storage_provider="s3",
            storage_key=f"v5d/{tenant_id}/projects/{project_id}/studio/v{v['version_number']}/export.glb",
            content_hash=content_hash,
            size_bytes=len(glb_bytes),
            mime_type="model/gltf-binary",
            producing_stage="studio_export",
            producing_version=v.get("version_number", 1),
        )
        db.add(dart)

        # Save locally for read-back verification
        import os as _os
        export_dir = _os.path.join(_os.path.dirname(__file__), "..", "..", ".exports")
        _os.makedirs(export_dir, exist_ok=True)
        glb_path = _os.path.join(export_dir, f"studio_v{v['version_number']}_{project_id}.glb")
        with open(glb_path, "wb") as f:
            f.write(glb_bytes)
        logger.info("studio_glb_saved", path=glb_path, size=len(glb_bytes))

        db.commit()

        # Generate manifest
        manifest = generate_studio_manifest(scene_data, studio_draft, {
            "project_id": str(project_id),
            "source_scene_version": v.get("source_scene_version", 1),
            "studio_version": v.get("version_number"),
            "studio_version_name": v.get("name", ""),
            "timestamp": v.get("created_at", ""),
            "content_hash": content_hash,
        })

        from fastapi.responses import Response
        return Response(
            content=glb_bytes,
            media_type="model/gltf-binary",
            headers={
                "Content-Disposition": f"attachment; filename=studio_v{v['version_number']}.glb",
                "X-Studio-Version": str(v.get("version_number", "")),
                "X-Source-Scene": str(v.get("source_scene_version", "")),
                "X-Content-Hash": content_hash,
                "X-Artifact-ID": str(dart.id),
                "X-GLB-Valid": str(validation.get("valid", False)),
                "X-Furniture-Count": str(len(studio_draft.get("furniture_instances", []))),
                "X-Manifest": _json.dumps(manifest, separators=(',', ':')),
            },
        )
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Placement Validation
# ═══════════════════════════════════════════════════════════

@router.post("/draft/{project_id}/validate-placement")
async def validate_placement(project_id: UUID, request: Request):
    """Validate furniture placement against room boundaries and collisions."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        scene_db = db.query(Scene3DVersion).filter(
            Scene3DVersion.project_id == project_id,
            Scene3DVersion.tenant_id == tenant_id,
        ).order_by(Scene3DVersion.version.desc()).first()

        scene_objects = (scene_db.scene_data or {}).get("objects", []) if scene_db else []
        furniture = body.get("furniture_instances", [])
        issues = []

        # Build room boundaries from scene objects
        rooms = {}
        for obj in scene_objects:
            if obj.get("type") == "room_volume":
                props = obj.get("properties", {})
                rooms[str(obj.get("id", ""))] = {
                    "bbox": props.get("bbox", {}),
                    "label": props.get("function") or obj.get("label", ""),
                    "area_m2": props.get("area_m2", 0),
                }

        # Build wall objects for collision
        walls = []
        for obj in scene_objects:
            if obj.get("type") == "wall_solid":
                walls.append({
                    "id": str(obj.get("id", "")),
                    "bbox": obj.get("properties", {}).get("bbox", {}),
                })

        # Build door objects for obstruction check
        doors = []
        for obj in scene_objects:
            if obj.get("type") == "door_element":
                doors.append({
                    "id": str(obj.get("id", "")),
                    "position": obj.get("properties", {}).get("position", [0, 0, 0]),
                    "bbox": obj.get("properties", {}).get("bbox", {}),
                    "width": obj.get("properties", {}).get("width", 900),
                })

        def bbox_overlap(a, b):
            """Check if two bounding boxes overlap."""
            if not a or not b:
                return False
            return (a.get("min_x", 0) < b.get("max_x", 99999) and
                    a.get("max_x", 0) > b.get("min_x", -1) and
                    a.get("min_y", -999) < b.get("max_y", 99999) and
                    a.get("max_y", 0) > b.get("min_y", -1) and
                    a.get("min_z", 0) < b.get("max_z", 99999) and
                    a.get("max_z", 0) > b.get("min_z", -1))

        # Build furniture library lookup for missing-asset check
        furniture_lib = {}
        for item in db.query(FurnitureLibraryItem).filter(FurnitureLibraryItem.is_global == True).all():
            furniture_lib[str(item.id)] = item.name

        for fi in furniture:
            fid = fi.get("instance_id", fi.get("asset_id", ""))
            pos = fi.get("position", [0, 0, 0])
            dims = fi.get("dimensions", [1000, 800, 600])

            # Compute furniture bbox
            fbbox = {
                "min_x": pos[0] - dims[0] / 2,
                "max_x": pos[0] + dims[0] / 2,
                "min_y": pos[1],
                "max_y": pos[1] + dims[1],
                "min_z": pos[2] - dims[2] / 2,
                "max_z": pos[2] + dims[2] / 2,
            }

            # Check room containment
            room_id = fi.get("room_id")
            if room_id and str(room_id) in rooms:
                rbbox = rooms[str(room_id)]["bbox"]
                if rbbox and not (
                    fbbox["min_x"] >= rbbox.get("min_x", -1e9) - 50 and
                    fbbox["max_x"] <= rbbox.get("max_x", 1e9) + 50 and
                    fbbox["min_z"] >= rbbox.get("min_z", -1e9) - 50 and
                    fbbox["max_z"] <= rbbox.get("max_z", 1e9) + 50
                ):
                    issues.append({
                        "object_id": fid, "severity": "warning",
                        "code": "OUTSIDE_ROOM",
                        "message": f"Furniture extends outside room boundary",
                        "suggested_action": "Move furniture fully inside the room",
                    })

            # Check wall intersection
            for wall in walls:
                wbbox = wall["bbox"]
                if bbox_overlap(fbbox, wbbox):
                    issues.append({
                        "object_id": fid, "severity": "blocking",
                        "code": "WALL_INTERSECTION",
                        "message": f"Furniture intersects wall {wall['id'][:8]}",
                        "suggested_action": "Move furniture away from walls",
                    })

            # Check furniture overlap
            for other in furniture:
                oid = other.get("instance_id", other.get("asset_id", ""))
                if oid == fid:
                    continue
                opos = other.get("position", [0, 0, 0])
                odims = other.get("dimensions", [1000, 800, 600])
                obbox = {
                    "min_x": opos[0] - odims[0] / 2,
                    "max_x": opos[0] + odims[0] / 2,
                    "min_y": opos[1],
                    "max_y": opos[1] + odims[1],
                    "min_z": opos[2] - odims[2] / 2,
                    "max_z": opos[2] + odims[2] / 2,
                }
                if bbox_overlap(fbbox, obbox):
                    issues.append({
                        "object_id": fid, "severity": "warning",
                        "code": "FURNITURE_OVERLAP",
                        "message": f"Furniture overlaps with another piece",
                        "suggested_action": "Move furniture apart to avoid overlap",
                    })

            # Check invalid scale
            sc = fi.get("scale", [1, 1, 1])
            if any(s < 0.01 or s > 20 for s in sc):
                issues.append({
                    "object_id": fid, "severity": "blocking",
                    "code": "INVALID_SCALE",
                    "message": f"Furniture scale {sc} is out of valid range [0.01, 20]",
                    "suggested_action": "Reset scale to a valid range",
                })

            # Check doorway obstruction
            for door in doors:
                dbbox = door.get("bbox", {})
                if dbbox and bbox_overlap(fbbox, dbbox):
                    dw = door.get("width", 900)
                    issues.append({
                        "object_id": fid, "severity": "blocking",
                        "code": "DOORWAY_OBSTRUCTION",
                        "message": f"Furniture obstructs doorway (door width: {dw}mm)",
                        "suggested_action": f"Move furniture at least {int(dw/2)}mm away from the door opening",
                    })

            # Check floor elevation
            elev = pos[1] if len(pos) > 1 else 0
            room_elev = 0  # default floor elevation
            if fi.get("room_id") and str(fi.get("room_id")) in rooms:
                rbbox = rooms[str(fi["room_id"])].get("bbox", {})
                room_elev = rbbox.get("min_y", 0)
            ELEV_TOLERANCE = 50  # mm
            if abs(elev - room_elev) > ELEV_TOLERANCE and fi.get("room_id"):
                issues.append({
                    "object_id": fid, "severity": "warning",
                    "code": "FLOOR_ELEVATION_MISMATCH",
                    "message": f"Furniture elevation {elev:.0f}mm differs from floor ({room_elev:.0f}mm)",
                    "suggested_action": f"Set elevation to match the floor at {room_elev:.0f}mm",
                })

            # Check missing asset
            asset_id = fi.get("asset_id", "")
            if asset_id and asset_id not in furniture_lib:
                issues.append({
                    "object_id": fid, "severity": "blocking",
                    "code": "MISSING_ASSET",
                    "message": f"Referenced furniture asset '{asset_id}' not found in library",
                    "suggested_action": "Remove this furniture instance or ensure the asset is loaded",
                })

        return {
            "validated": True,
            "furniture_count": len(furniture),
            "issues": issues,
            "blocking": sum(1 for i in issues if i["severity"] == "blocking"),
            "warnings": sum(1 for i in issues if i["severity"] == "warning"),
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Storage Abstraction Verification
# ═══════════════════════════════════════════════════════════

@router.get("/artifacts/{project_id}")
async def list_studio_artifacts(project_id: UUID, request: Request):
    """List all studio artifacts for a project."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.studio.storage import storage_provider
        artifacts = storage_provider.list_artifacts(db, project_id, tenant_id)
        return {"project_id": str(project_id), "artifacts": artifacts, "total": len(artifacts)}
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/verify")
async def verify_artifact(artifact_id: UUID, request: Request):
    """Read back and hash-verify a stored artifact."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.studio.storage import storage_provider
        result = storage_provider.verify_artifact(db, artifact_id)
        return result
    finally:
        db.close()


@router.get("/artifacts/{artifact_id}/inspect")
async def inspect_exported_glb(artifact_id: UUID, request: Request):
    """Independently inspect an exported Studio GLB artifact."""
    user_id, tenant_id = _get_user_tenant(request)
    db = SessionLocal()
    try:
        from packages.studio.storage import storage_provider
        from packages.studio.glb_inspector import GLBInspector

        result = storage_provider.read_artifact(db, artifact_id)
        if not result or not result.get("data"):
            return {"error": "Artifact not found or hash mismatch", "artifact_id": str(artifact_id)}

        inspector = GLBInspector(result["data"])
        summary = inspector.get_object_summary()

        return {
            "artifact_id": str(artifact_id),
            "glb_valid": inspector.valid,
            "glb_version": inspector.version,
            "node_count": inspector.node_count,
            "mesh_count": inspector.mesh_count,
            "material_count": inspector.material_count,
            "furniture_objects": summary["furniture_objects"],
            "architectural_objects": summary["architectural_objects"][:20],
            "materials": summary["materials_summary"],
            "errors": inspector.errors,
            "hash_match": result.get("hash_match", False),
            "storage_key": result.get("storage_key", ""),
            "size_bytes": result.get("size_bytes", 0),
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Offline Reconciliation
# ═══════════════════════════════════════════════════════════

@router.post("/draft/{project_id}/sync")
async def sync_offline_edits(project_id: UUID, request: Request):
    """Synchronize pending offline edits without creating duplicates."""
    user_id, tenant_id = _get_user_tenant(request)
    body = await request.json()
    db = SessionLocal()
    try:
        draft_data = load_draft(db, project_id, tenant_id)
        if not draft_data:
            raise HTTPException(404, "No draft found")

        draft_id = UUID(draft_data["draft_id"])
        pending = body.get("pending_operations", [])
        last_server_seq = body.get("last_server_sequence", 0)

        # Get current server sequence
        current_seq = db.query(StudioEditOperation).filter(
            StudioEditOperation.draft_id == draft_id
        ).count()

        synced = []
        for op in pending:
            client_seq = op.get("client_sequence", 0)
            if client_seq <= current_seq:
                # Already on server, skip
                continue

            # Check for duplicate by (type + target + timestamp window)
            existing = db.query(StudioEditOperation).filter(
                StudioEditOperation.draft_id == draft_id,
                StudioEditOperation.operation_type == op.get("operation_type"),
                StudioEditOperation.target_object_id == UUID(op.get("target_object_id")) if op.get("target_object_id") else None,
            ).order_by(StudioEditOperation.sequence.desc()).first()

            if existing and existing.sequence >= current_seq:
                synced.append({"client_sequence": client_seq, "status": "skipped_duplicate"})
                continue

            rec = record_edit(db, draft_id, {
                "operation_type": op.get("operation_type", "unknown"),
                "target_object_id": op.get("target_object_id"),
                "object_type": op.get("object_type", ""),
                "before_state": op.get("before_state", {}),
                "after_state": op.get("after_state", {}),
                "user_id": str(user_id),
            })
            synced.append({
                "client_sequence": client_seq,
                "status": "synced",
                "server_sequence": rec.sequence,
            })

        return {
            "synced_count": len([s for s in synced if s["status"] == "synced"]),
            "skipped_duplicates": len([s for s in synced if s["status"] == "skipped_duplicate"]),
            "current_server_sequence": db.query(StudioEditOperation).filter(
                StudioEditOperation.draft_id == draft_id
            ).count(),
            "operations": synced,
        }
    finally:
        db.close()
