import sys, os, traceback
sys.path.insert(0, r"C:\Users\admin\workspaces\vision-5d")
from uuid import UUID
from packages.domain.database import SessionLocal
from packages.domain.models import UnderstandingGraph, GraphNode, GraphEdge
from packages.plan_understanding.contracts import (
    ArchitecturalGraph, GraphNode as P2Node, GraphEdge as P2Edge,
    GraphNodeType, GraphEdgeType, ScaleCalibration, ScaleMethod,
)

db = SessionLocal()
ug = db.query(UnderstandingGraph).filter(UnderstandingGraph.is_complete == True).order_by(UnderstandingGraph.created_at.desc()).first()
nodes = db.query(GraphNode).filter(GraphNode.graph_id == ug.id).all()
edges = db.query(GraphEdge).filter(GraphEdge.graph_id == ug.id).all()
graph = ArchitecturalGraph(
    graph_id=ug.id, project_id=ug.project_id,
    source_asset_id=ug.source_asset_id or UUID("00000000-0000-0000-0000-00000000000a"),
    nodes=[P2Node(node_id=n.id, node_type=GraphNodeType(n.node_type), label=n.label,
            properties=n.properties or {}, detection_ref=n.detection_ref, confidence=n.confidence, source=n.source or "") for n in nodes],
    edges=[P2Edge(edge_id=e.id, source_id=e.source_node_id, target_id=e.target_node_id,
            edge_type=GraphEdgeType(e.edge_type), properties=e.properties or {}, confidence=e.confidence) for e in edges],
    scale=ScaleCalibration(method=ScaleMethod.AUTO, scale_ratio="1:1", confidence=0.5),
    is_complete=True, metadata={},
)
from packages.geometry.pipeline import geometry_pipeline
gres = geometry_pipeline.process(ug.project_id, graph=graph)
m = gres.model
print("geometry model:", m.model_id, "floors", len(m.floors))

from packages.domain.persistence import persist_geometry_model
print("about to persist...")
try:
    model_db = persist_geometry_model(
        db, ug.tenant_id, ug.project_id, ug.id, 1,
        job_id=UUID("00000000-0000-0000-0000-00000000000a"),
        p3_model=m,
    )
    print("PERSIST OK:", model_db.id)
except Exception:
    traceback.print_exc()
