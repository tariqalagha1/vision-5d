"""
Vision 5D — Persistence Layer for Phase 2 and Phase 3
Wires pipeline outputs to database tables with version lineage.
"""
import json
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
import structlog

from packages.domain.models import (
    UnderstandingGraph, GraphNode, GraphEdge,
    PersistedGeometry, GeometryFloor, GeometryWall, GeometryRoom, GeometryOpening, GeometryEdit,
)
from packages.domain.database import SessionLocal

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
# Phase 2 — Understanding Graph Persistence
# ═══════════════════════════════════════════════════════════

def persist_understanding_graph(
    db: Session,
    tenant_id: UUID,
    project_id: UUID,
    source_asset_id: UUID,
    job_id: UUID,
    p2_graph,  # ArchitecturalGraph pydantic model
    source_graph_id: UUID = None,
) -> UnderstandingGraph:
    """Persist a Phase 2 architectural graph with all nodes and edges.

    Returns the persisted DB row with version lineage.
    """
    # Determine version
    existing = db.query(UnderstandingGraph).filter(
        UnderstandingGraph.project_id == project_id,
        UnderstandingGraph.tenant_id == tenant_id,
    ).order_by(UnderstandingGraph.version.desc()).first()

    version = (existing.version + 1) if existing else 1

    # Create graph record
    graph_db = UnderstandingGraph(
        tenant_id=tenant_id,
        project_id=project_id,
        source_asset_id=source_asset_id,
        source_graph_id=source_graph_id or (existing.id if existing else None),
        job_id=job_id,
        state="COMPLETED" if p2_graph.is_complete else "PARTIAL",
        version=version,
        is_complete=p2_graph.is_complete,
        completeness_issues=p2_graph.completeness_issues,
        scale_ratio=p2_graph.scale.scale_ratio if p2_graph.scale else None,
        scale_confidence=p2_graph.scale.confidence if p2_graph.scale else 0.0,
        graph_metadata=p2_graph.metadata,
    )
    db.add(graph_db)
    db.flush()

    # Persist nodes
    for node in p2_graph.nodes:
        node_db = GraphNode(
            graph_id=graph_db.id,
            node_type=node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
            label=node.label,
            properties=node.properties,
            detection_ref=node.detection_ref,
            confidence=node.confidence,
            source=node.source,
        )
        db.add(node_db)

    # Persist edges
    for edge in p2_graph.edges:
        edge_db = GraphEdge(
            graph_id=graph_db.id,
            source_node_id=edge.source_id,
            target_node_id=edge.target_id,
            edge_type=edge.edge_type.value if hasattr(edge.edge_type, 'value') else str(edge.edge_type),
            properties=edge.properties,
            confidence=edge.confidence,
        )
        db.add(edge_db)

    db.commit()
    logger.info("understanding_graph_persisted",
                graph_id=str(graph_db.id), version=version,
                nodes=len(p2_graph.nodes), edges=len(p2_graph.edges))

    return graph_db


def load_understanding_graph(db: Session, graph_id: UUID) -> dict:
    """Load a persisted understanding graph with all nodes and edges."""
    graph = db.query(UnderstandingGraph).filter(UnderstandingGraph.id == graph_id).first()
    if not graph:
        return None

    nodes = db.query(GraphNode).filter(GraphNode.graph_id == graph_id).all()
    edges = db.query(GraphEdge).filter(GraphEdge.graph_id == graph_id).all()

    return {
        "graph": graph,
        "nodes": nodes,
        "edges": edges,
    }


# ═══════════════════════════════════════════════════════════
# Phase 3 — Geometry Model Persistence
# ═══════════════════════════════════════════════════════════

def persist_geometry_model(
    db: Session,
    tenant_id: UUID,
    project_id: UUID,
    source_graph_id: UUID,
    source_graph_version: int,
    job_id: UUID,
    p3_model,  # GeometryModel pydantic model (from geometry.contracts)
    scale_px_per_mm: float = 0.0,
    scale_ratio: str = "1:1",
    scale_confidence: float = 0.0,
) -> PersistedGeometry:
    """Persist a Phase 3 geometry model with floors, walls, rooms, openings.

    Returns the persisted DB row with version lineage.
    """
    existing = db.query(PersistedGeometry).filter(
        PersistedGeometry.project_id == project_id,
        PersistedGeometry.tenant_id == tenant_id,
    ).order_by(PersistedGeometry.version.desc()).first()

    version = (existing.version + 1) if existing else 1

    model_db = PersistedGeometry(
        tenant_id=tenant_id,
        project_id=project_id,
        source_graph_id=source_graph_id,
        source_graph_version=source_graph_version,
        job_id=job_id,
        state="COMPLETED" if p3_model.is_complete else "PARTIAL",
        version=version,
        is_complete=p3_model.is_complete,
        completeness_issues=p3_model.completeness_issues or [],
        scale_px_per_mm=scale_px_per_mm,
        scale_ratio=scale_ratio,
        scale_confidence=scale_confidence,
        units="mm",
        model_metadata={
            "pipeline_version": "3.0.0",
            "repairs": p3_model.repair_log.total_repairs if p3_model.repair_log else 0,
            "ambiguities": p3_model.ambiguity_report.total if p3_model.ambiguity_report else 0,
        },
    )
    db.add(model_db)
    db.flush()

    # Persist floors
    for floor in p3_model.floors:
        floor_db = GeometryFloor(
            model_id=model_db.id,
            floor_number=floor.floor_number,
            label=floor.label,
            elevation_mm=floor.elevation_mm,
            outline=[(p.x, p.y) for p in floor.outline] if floor.outline else [],
        )
        db.add(floor_db)
        db.flush()

        # Persist walls
        wall_id_map = {}  # centerline_id → db_id
        for wall in floor.walls:
            wall_db = GeometryWall(
                floor_id=floor_db.id,
                centerline=[(p.x, p.y) for p in wall.centerline],
                face_left=[(p.x, p.y) for p in wall.face_left],
                face_right=[(p.x, p.y) for p in wall.face_right],
                thickness_mm=wall.thickness,
                polygon=[(p.x, p.y) for p in wall.polygon],
                is_external=wall.is_external,
                confidence=wall.confidence,
                state=wall.state.value if hasattr(wall.state, 'value') else str(wall.state),
                source_graph_node_id=wall.source_graph_ref,
            )
            db.add(wall_db)
            wall_id_map[wall.centerline_id] = wall_db.id

        db.flush()

        # Persist rooms
        room_id_map = {}
        for room in floor.rooms:
            room_db = GeometryRoom(
                floor_id=floor_db.id,
                label=room.label,
                function=room.function,
                polygon=[(p.x, p.y) for p in room.polygon],
                area_mm2=room.area_mm2,
                area_m2=room.area_m2(),
                perimeter_mm=room.perimeter_mm,
                centroid_x=room.centroid.x,
                centroid_y=room.centroid.y,
                wall_ids=[str(w) for w in room.wall_ids],
                opening_ids=[str(o) for o in room.opening_ids],
                adjacent_room_ids=[str(a) for a in room.adjacent_room_ids],
                is_closed=room.is_closed,
                confidence=room.confidence,
                state=room.state.value if hasattr(room.state, 'value') else str(room.state),
                source_graph_node_id=room.graph_node_ref,
            )
            db.add(room_db)
            room_id_map[room.room_id] = room_db.id

        db.flush()

        # Persist openings
        for opening in floor.openings:
            host_wall_db_id = wall_id_map.get(opening.host_wall_id) if opening.host_wall_id else None
            op_db = GeometryOpening(
                floor_id=floor_db.id,
                opening_type=opening.opening_type.value if hasattr(opening.opening_type, 'value') else str(opening.opening_type),
                host_wall_id=host_wall_db_id,
                position_along_wall=opening.position_along_wall,
                position_x=opening.position.x,
                position_y=opening.position.y,
                width_mm=opening.width_mm,
                height_mm=opening.height_mm,
                orientation_deg=opening.orientation_deg,
                swing=opening.swing.value if hasattr(opening.swing, 'value') else str(opening.swing),
                sill_height_mm=opening.sill_height_mm,
                connects_room_a=opening.connects_room_a,
                connects_room_b=opening.connects_room_b,
                is_valid=opening.is_valid,
                validation_issues=opening.validation_issues,
                confidence=opening.confidence,
                state=opening.state.value if hasattr(opening.state, 'value') else str(opening.state),
                source_graph_node_id=opening.graph_node_ref,
            )
            db.add(op_db)

    db.commit()
    logger.info("geometry_model_persisted",
                model_id=str(model_db.id), version=version,
                walls=sum(len(f.walls) for f in p3_model.floors),
                rooms=sum(len(f.rooms) for f in p3_model.floors),
                openings=sum(len(f.openings) for f in p3_model.floors))

    return model_db


def persist_geometry_edit(
    db: Session,
    model_id: UUID,
    edit_type: str,
    object_ref: UUID = None,
    params: dict = None,
    previous_state: dict = None,
    version_before: int = 0,
    version_after: int = 0,
) -> GeometryEdit:
    """Record a geometry edit in the edit history."""
    edit_db = GeometryEdit(
        model_id=model_id,
        edit_type=edit_type,
        object_ref=object_ref,
        params=params or {},
        previous_state=previous_state,
        version_before=version_before,
        version_after=version_after,
    )
    db.add(edit_db)
    db.commit()
    return edit_db


def load_geometry_model(db: Session, model_id: UUID) -> dict:
    """Load a persisted geometry model with all components."""
    model = db.query(PersistedGeometry).filter(PersistedGeometry.id == model_id).first()
    if not model:
        return None

    floors = db.query(GeometryFloor).filter(GeometryFloor.model_id == model_id).all()
    result = {"model": model, "floors": []}

    for floor in floors:
        walls = db.query(GeometryWall).filter(GeometryWall.floor_id == floor.id).all()
        rooms = db.query(GeometryRoom).filter(GeometryRoom.floor_id == floor.id).all()
        openings = db.query(GeometryOpening).filter(GeometryOpening.floor_id == floor.id).all()
        result["floors"].append({
            "floor": floor, "walls": walls, "rooms": rooms, "openings": openings,
        })

    result["edits"] = db.query(GeometryEdit).filter(
        GeometryEdit.model_id == model_id
    ).order_by(GeometryEdit.applied_at).all()

    return result


def list_geometry_versions(db: Session, project_id: UUID, tenant_id: UUID) -> list:
    """List all geometry model versions for a project."""
    return db.query(PersistedGeometry).filter(
        PersistedGeometry.project_id == project_id,
        PersistedGeometry.tenant_id == tenant_id,
    ).order_by(PersistedGeometry.version.desc()).all()
