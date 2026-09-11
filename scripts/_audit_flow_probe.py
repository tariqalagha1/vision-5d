import sys, os, json, traceback, time
sys.path.insert(0, r"C:\Users\admin\workspaces\vision-5d")

from uuid import UUID, uuid4
from packages.domain.database import SessionLocal
from packages.domain.models import UnderstandingGraph, GraphNode, GraphEdge
from packages.plan_understanding.contracts import (
    ArchitecturalGraph, GraphNode as P2Node, GraphEdge as P2Edge,
    GraphNodeType, GraphEdgeType, ScaleCalibration, ScaleMethod,
)

db = SessionLocal()
try:
    ug = db.query(UnderstandingGraph).filter(
        UnderstandingGraph.is_complete == True
    ).order_by(UnderstandingGraph.created_at.desc()).first()
    print("Reference graph:", ug.id, "project:", ug.project_id, "tenant:", ug.tenant_id)

    nodes = db.query(GraphNode).filter(GraphNode.graph_id == ug.id).all()
    edges = db.query(GraphEdge).filter(GraphEdge.graph_id == ug.id).all()

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

    # 1. Geometry pipeline
    from packages.geometry.pipeline import geometry_pipeline
    print("\n[1] Geometry pipeline...")
    gres = geometry_pipeline.process(ug.project_id, graph=graph)
    if not gres.model:
        print("   FAIL: no geometry model. stages_failed:", gres.stages_failed)
        raise SystemExit(1)
    m = gres.model
    wc = sum(len(f.walls) for f in m.floors)
    rc = sum(len(f.rooms) for f in m.floors)
    oc = sum(len(f.openings) for f in m.floors)
    print(f"   OK: {len(m.floors)} floors, {wc} walls, {rc} rooms, {oc} openings")

    # 2. Persist geometry
    from packages.domain.persistence import persist_geometry_model
    print("\n[2] Persist geometry...")
    try:
        model_db = persist_geometry_model(
            db, ug.tenant_id, ug.project_id, ug.id, 1,
            job_id=uuid4(),
            p3_model=m,
        )
        print("   OK: persisted geometry model id:", model_db.id, "v", model_db.version)
    except Exception as e:
        print("   FAIL persist geometry:", type(e).__name__, e)
        traceback.print_exc()

    # 3. Scene3D reconstruction
    from packages.scene3d.reconstruction import scene3d_pipeline
    print("\n[3] Scene3D reconstruction...")
    sres = scene3d_pipeline.process(m, tenant_id=ug.tenant_id, workspace_id=None, job_id=None)
    if not sres.scene:
        print("   FAIL: no scene. stages_failed:", sres.stages_failed)
        raise SystemExit(1)
    scene = sres.scene
    print(f"   OK: scene with {len(scene.meshes)} meshes")
    for ms in scene.meshes[:5]:
        print(f"      mesh type={ms.object_type.value} verts={ms.vertex_count} tris={ms.triangle_count} valid={ms.is_valid}")
    if scene.statistics:
        print("   stats:", scene.statistics.model_dump())

    # 4. GLB export + validate
    from packages.scene3d.glb_export import export_glb, validate_glb
    print("\n[4] GLB export + validate...")
    try:
        glb = export_glb(scene)
        v = validate_glb(glb)
        print(f"   GLB bytes={len(glb)} valid={v.get('valid')} sha256={v.get('sha256','')[:16]}")
        if v.get('errors'):
            print("   errors:", v['errors'][:5])
        out = os.path.join(r"C:\Users\admin\workspaces\vision-5d", ".exports", "probe_scene.glb")
        with open(out, "wb") as f:
            f.write(glb)
        print("   saved:", out)
    except Exception as e:
        print("   FAIL glb:", type(e).__name__, e)
        traceback.print_exc()

    # 5. Persist scene3d
    from packages.scene3d.persistence import persist_scene3d
    print("\n[5] Persist scene3d...")
    try:
        scene_db = persist_scene3d(db, scene)
        print("   OK: persisted scene3d id:", scene_db.id, "v", scene_db.version)
    except Exception as e:
        print("   FAIL persist scene3d:", type(e).__name__, e)
        traceback.print_exc()

    db.commit()
    print("\nDONE")
finally:
    db.close()
