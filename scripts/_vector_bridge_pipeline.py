#!/usr/bin/env python3
"""Lossless vector bridge: real DXF -> ArchitecturalGraph -> Geometry -> Scene3D -> GLB.

The production path (plan_pipeline CV on a rasterized image) collapses the
full building to ~4 walls. This builds the graph DIRECTLY from CAD vector data
via the fidelity bridge, then runs the same geometry/scene3d/glb_export stages.
"""
import os, sys, json, time, hashlib, struct
from uuid import uuid4
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.cad_import.dxf_parser import DXFParser
from packages.cad_import.fidelity_bridge import CADFidelityBridge
from packages.plan_understanding.contracts import (
    ArchitecturalGraph, GraphNode, GraphEdge, GraphNodeType, GraphEdgeType,
    ScaleCalibration, ScaleMethod,
)
from packages.geometry.pipeline import geometry_pipeline
from packages.scene3d.reconstruction import scene3d_pipeline
from packages.scene3d.glb_export import export_glb, validate_glb

DXF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "RE-SingDetch-FH_AS", "geometry", "converted.dxf")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence", "runs", "vision5d-final-certification-repair-001")
os.makedirs(OUT_DIR, exist_ok=True)


def build_graph_from_vector(dxf_content: str):
    parser = DXFParser()
    drawing = parser.parse(dxf_content)
    bridge = CADFidelityBridge(drawing)
    bridge.extract_all()

    nodes = []
    # Walls -> WALL nodes (centerline = [ [x1,y1], [x2,y2] ])
    for w in bridge.walls:
        nodes.append(GraphNode(
            node_type=GraphNodeType.WALL, label=w.id,
            properties={"centerline": [[w.x1, w.y1], [w.x2, w.y2]],
                        "thickness_mm": w.thickness},
            confidence=1.0, source="cad_vector",
        ))
    # Doors + windows -> OPENING nodes
    for o in list(bridge.doors) + list(bridge.windows):
        cls = o.opening_type if hasattr(o, "opening_type") else "door"
        w = getattr(o, "width", 900.0)
        nodes.append(GraphNode(
            node_type=GraphNodeType.OPENING, label=o.id,
            properties={"class": cls, "bbox": [o.x - w / 2, o.y - w / 2, w, w]},
            confidence=0.9, source="cad_vector",
        ))
    # Rooms -> ROOM nodes
    for r in bridge.rooms:
        nodes.append(GraphNode(
            node_type=GraphNodeType.ROOM, label=r.label,
            properties={"function": r.label},
            confidence=0.8, source="cad_vector",
        ))

    scale = ScaleCalibration(
        method=ScaleMethod.AUTO, units="mm", pixels_per_unit=1.0 / 25.4,
        scale_ratio="1:1", confidence=0.9, manual_override=True,
    )
    graph = ArchitecturalGraph(
        project_id=uuid4(), source_asset_id=uuid4(),
        nodes=nodes, edges=[],
        scale=scale,
        metadata={"width_px": drawing.width, "height_px": drawing.height,
                  "source": "cad_vector_fidelity_bridge"},
        is_complete=True,
    )
    return graph, drawing, bridge


def main():
    t0 = time.time()
    dxf = open(DXF_PATH, encoding="utf-8", errors="replace").read()
    src_sha = hashlib.sha256(dxf.encode("utf-8", "replace")).hexdigest()

    graph, drawing, bridge = build_graph_from_vector(dxf)
    print(f"=== VECTOR GRAPH ===")
    print(f"  walls(nodes):  {sum(1 for n in graph.nodes if n.node_type==GraphNodeType.WALL)}")
    print(f"  openings:      {sum(1 for n in graph.nodes if n.node_type==GraphNodeType.OPENING)}")
    print(f"  rooms:         {sum(1 for n in graph.nodes if n.node_type==GraphNodeType.ROOM)}")
    print(f"  bounds:        {drawing.bounds} ({drawing.width:.1f} x {drawing.height:.1f})")
    print(f"  source sha256: {src_sha[:24]}")

    pid = uuid4()
    p3 = geometry_pipeline.process(pid, graph=graph)
    model = p3.model
    print(f"\n=== GEOMETRY ===")
    print(f"  stages ok:  {len(p3.stages_completed)}, failed: {len(p3.stages_failed)}")
    if model and model.floors:
        f = model.floors[0]
        print(f"  walls:      {len(f.walls)}")
        print(f"  rooms:      {len(f.rooms)}")
        print(f"  openings:   {len(f.openings)}")
    if p3.stages_failed:
        print(f"  FAILURES:   {p3.stages_failed}")
        return

    scene_res = scene3d_pipeline.process(model)
    scene = scene_res.scene
    print(f"\n=== SCENE3D ===")
    if scene and scene.statistics:
        s = scene.statistics
        print(f"  meshes:     {s.mesh_count}")
        print(f"  vertices:   {s.vertex_count}")
        print(f"  triangles:  {s.triangle_count}")
        print(f"  rooms:      {s.room_count}")
        print(f"  floor m2:   {s.total_floor_area_m2:.1f}")
    if scene is None or not scene.meshes:
        print("  NO MESHES — scene assembly failed")
        return

    glb = export_glb(scene)
    val = validate_glb(glb)
    glb_path = os.path.join(OUT_DIR, "RE-SingDetch-FH_AS.glb")
    open(glb_path, "wb").write(glb)
    glb_sha = hashlib.sha256(glb).hexdigest()
    print(f"\n=== GLB ===")
    print(f"  bytes:      {len(glb)}")
    print(f"  sha256:     {glb_sha}")
    print(f"  valid:      {val.get('valid')}")
    print(f"  errors:     {val.get('errors', [])[:5]}")
    print(f"  path:       {glb_path}")

    # summary json
    summary = {
        "source": DXF_PATH,
        "source_sha256": src_sha,
        "source_bounds": list(drawing.bounds),
        "graph_wall_nodes": sum(1 for n in graph.nodes if n.node_type==GraphNodeType.WALL),
        "graph_openings": sum(1 for n in graph.nodes if n.node_type==GraphNodeType.OPENING),
        "graph_rooms": sum(1 for n in graph.nodes if n.node_type==GraphNodeType.ROOM),
        "geometry_walls": len(model.floors[0].walls) if model and model.floors else 0,
        "geometry_rooms": len(model.floors[0].rooms) if model and model.floors else 0,
        "geometry_openings": len(model.floors[0].openings) if model and model.floors else 0,
        "scene_meshes": scene.statistics.mesh_count if scene and scene.statistics else 0,
        "scene_vertices": scene.statistics.vertex_count if scene and scene.statistics else 0,
        "scene_triangles": scene.statistics.triangle_count if scene and scene.statistics else 0,
        "glb_bytes": len(glb),
        "glb_sha256": glb_sha,
        "glb_valid": val.get("valid"),
        "glb_errors": val.get("errors", []),
        "walltime_s": round(time.time() - t0, 1),
    }
    json.dump(summary, open(os.path.join(OUT_DIR, "pipeline_summary.json"), "w"), indent=2, default=str)
    print(f"\n  summary written")


if __name__ == "__main__":
    main()
