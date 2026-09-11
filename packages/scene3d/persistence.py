"""
Vision 5D — Phase 4 Scene Persistence Layer
Persists Scene3D objects to the database with version lineage.
"""
import json as _json, structlog
from uuid import UUID
from sqlalchemy.orm import Session

from packages.domain.models import (
    Base, new_uuid, Scene3DVersion, Scene3DObject, Scene3DMesh,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
# Persistence Functions
# ═══════════════════════════════════════════════════════════

def persist_scene3d(
    db: Session,
    scene,  # Scene3D pydantic model
) -> Scene3DVersion:
    """Persist a complete Scene3D to the database."""
    from packages.domain.models import Scene3DVersion as S3DV, Scene3DObject as S3DO, Scene3DMesh as S3DM

    # Determine version
    existing = db.query(S3DV).filter(
        S3DV.project_id == scene.project_id,
        S3DV.tenant_id == scene.tenant_id,
    ).order_by(S3DV.version.desc()).first()
    version = (existing.version + 1) if existing else 1

    # Compute bbox
    bbox = scene.statistics.bbox if scene.statistics else None

    scene_db = S3DV(
        tenant_id=scene.tenant_id,
        workspace_id=scene.workspace_id,
        project_id=scene.project_id,
        source_geometry_model_id=scene.source_geometry_model_id,
        source_geometry_version=scene.source_geometry_version,
        source_graph_id=scene.source_graph_id,
        source_graph_version=scene.source_graph_version,
        job_id=scene.job_id,
        pipeline_version=scene.pipeline_version,
        version=version,
        state=scene.state.value if hasattr(scene.state, 'value') else str(scene.state),
        is_complete=scene.is_complete,
        completeness_issues=scene.completeness_issues,
        coordinate_system=scene.coordinate_system,
        unit_system=scene.unit_system,
        lineage=scene.lineage,
        scene_data=scene.model_dump(mode='json') if hasattr(scene, 'model_dump') else {},
        statistics=scene.statistics.model_dump(mode='json') if scene.statistics and hasattr(scene.statistics, 'model_dump') else {},
        bbox_min_x=bbox.min.x if bbox else None,
        bbox_min_y=bbox.min.y if bbox else None,
        bbox_min_z=bbox.min.z if bbox else None,
        bbox_max_x=bbox.max.x if bbox else None,
        bbox_max_y=bbox.max.y if bbox else None,
        bbox_max_z=bbox.max.z if bbox else None,
        vertex_count=scene.statistics.vertex_count if scene.statistics else 0,
        triangle_count=scene.statistics.triangle_count if scene.statistics else 0,
        artifact_refs=scene.artifact_refs,
    )
    db.add(scene_db)
    db.flush()

    # Persist scene objects
    if scene.building:
        for level in scene.building.levels:
            for wall in level.walls:
                db.add(S3DO(
                    scene_id=scene_db.id, object_type="wall_solid",
                    source_id=wall.source_wall_id, level_id=level.level_id,
                    label=f"Wall", position_x=0, position_y=0, position_z=0,
                ))
            for room in level.rooms:
                db.add(S3DO(
                    scene_id=scene_db.id, object_type="room_volume",
                    source_id=room.source_room_id, level_id=level.level_id,
                    label=room.label, properties={
                        "area_m2": room.floor_area_m2,
                        "function": room.function,
                        "is_closed": room.is_closed,
                    },
                ))
            for door in level.doors:
                db.add(S3DO(
                    scene_id=scene_db.id, object_type="door_element",
                    source_id=door.source_opening_id, level_id=level.level_id,
                    label=f"Door",
                ))
            for win in level.windows:
                db.add(S3DO(
                    scene_id=scene_db.id, object_type="window_element",
                    source_id=win.source_opening_id, level_id=level.level_id,
                    label=f"Window",
                ))

    # Persist meshes
    for mi, mesh in enumerate(scene.meshes):
        db.add(S3DM(
            scene_id=scene_db.id, object_id=mesh.object_id,
            object_type=mesh.object_type.value if hasattr(mesh.object_type, 'value') else str(mesh.object_type),
            vertex_count=mesh.vertex_count, triangle_count=mesh.triangle_count,
            material_id=mesh.material_id,
            mesh_data={
                "vertex_count": mesh.vertex_count,
                "triangle_count": mesh.triangle_count,
                "indices_count": len(mesh.indices),
                # Full data stored in S3; DB holds reference metadata
            },
            is_valid=mesh.is_valid,
            validation_issues=mesh.validation_issues,
        ))

    db.commit()
    logger.info("scene3d_persisted", scene_id=str(scene_db.id),
                version=version, vertices=scene_db.vertex_count,
                triangles=scene_db.triangle_count)

    return scene_db


def load_scene3d(db: Session, scene_id: UUID) -> dict:
    """Load a persisted Scene3DVersion with its objects and meshes."""
    from packages.domain.models import Scene3DVersion as S3DV, Scene3DObject as S3DO, Scene3DMesh as S3DM

    scene = db.query(S3DV).filter(S3DV.id == scene_id).first()
    if not scene:
        return None

    objects = db.query(S3DO).filter(S3DO.scene_id == scene_id).all()
    meshes = db.query(S3DM).filter(S3DM.scene_id == scene_id).all()

    return {
        "scene": scene,
        "objects": objects,
        "meshes": meshes,
    }


def list_scene3d_versions(db: Session, project_id: UUID, tenant_id: UUID) -> list:
    """List all scene versions for a project."""
    from packages.domain.models import Scene3DVersion as S3DV
    return db.query(S3DV).filter(
        S3DV.project_id == project_id,
        S3DV.tenant_id == tenant_id,
    ).order_by(S3DV.version.desc()).all()
