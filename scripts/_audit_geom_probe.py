import sys, os, json, traceback
sys.path.insert(0, r"C:\Users\admin\workspaces\vision-5d")

from uuid import UUID
from packages.domain.database import SessionLocal
from packages.domain.models import UnderstandingGraph, GraphNode, GraphEdge
from packages.plan_understanding.contracts import (
    ArchitecturalGraph, GraphNode as P2Node, GraphEdge as P2Edge,
    GraphNodeType, GraphEdgeType, ScaleCalibration, ScaleMethod,
)

db = SessionLocal()
try:
    # Pick the most recent complete understanding graph
    ug = db.query(UnderstandingGraph).filter(
        UnderstandingGraph.is_complete == True
    ).order_by(UnderstandingGraph.created_at.desc()).first()
    print("Reference understanding graph:", ug.id, "project:", ug.project_id, "asset:", ug.source_asset_id)

    nodes = db.query(GraphNode).filter(GraphNode.graph_id == ug.id).all()
    edges = db.query(GraphEdge).filter(GraphEdge.graph_id == ug.id).all()
    from collections import Counter
    print("node types:", dict(Counter(n.node_type for n in nodes)))
    print("edges:", len(edges))

    # Build ArchitecturalGraph
    graph = ArchitecturalGraph(
        graph_id=ug.id, project_id=ug.project_id,
        source_asset_id=ug.source_asset_id or UUID("00000000-0000-0000-0000-00000000000a"),
        nodes=[P2Node(node_id=n.id, node_type=GraphNodeType(n.node_type),
                label=n.label, properties=n.properties or {},
                detection_ref=n.detection_ref, confidence=n.confidence, source=n.source or "")
               for n in nodes],
        edges=[P2Edge(edge_id=e.id, source_id=e.source_node_id, target_id=e.target_node_id,
                edge_type=GraphEdgeType(e.edge_type), properties=e.properties or {}, confidence=e.confidence)
               for e in edges],
        scale=ScaleCalibration(method=ScaleMethod.AUTO, scale_ratio="1:1", confidence=0.5),
        is_complete=True, metadata={},
    )
    print("ArchitecturalGraph built OK")

    # Run geometry pipeline
    from packages.geometry.pipeline import geometry_pipeline
    print("\nRunning geometry pipeline...")
    result = geometry_pipeline.process(ug.project_id, graph=graph)
    print("stages_completed:", result.stages_completed)
    print("stages_failed:", result.stages_failed)
    if result.model:
        m = result.model
        floors = m.floors
        wc = sum(len(f.walls) for f in floors)
        rc = sum(len(f.rooms) for f in floors)
        oc = sum(len(f.openings) for f in floors)
        print(f"GEOMETRY RESULT: {len(floors)} floors, {wc} walls, {rc} rooms, {oc} openings")
        print("is_complete:", m.is_complete)
        print("state:", m.state)
        if m.validation:
            print("validation: pass=%s fail=%s clean=%s" % (m.validation.pass_count, m.validation.fail_count, m.validation.is_clean))
    else:
        print("NO MODEL PRODUCED")
finally:
    db.close()
