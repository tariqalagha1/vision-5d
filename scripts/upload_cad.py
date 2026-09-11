#!/usr/bin/env python3
"""
Vision 5D — Universal CAD Upload CLI
Accepts any supported format, auto-detects, imports, and runs the full pipeline.

Usage:
    python3 scripts/upload_cad.py path/to/file.dxf
    python3 scripts/upload_cad.py path/to/file.pdf
    python3 scripts/upload_cad.py path/to/file.ifc
    python3 scripts/upload_cad.py --detect path/to/file.ext
"""
import sys, os, time, json, hashlib, argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["V5D_AUTO_CREATE_TABLES"] = "true"

from packages.universal_ingestion import ingest_file, detect_format, supported_formats
from packages.universal_ingestion.dwg_production import register_production_dwg
register_production_dwg()

from packages.plan_understanding.pipeline import plan_pipeline
from packages.geometry.pipeline import geometry_pipeline
from packages.scene3d.reconstruction import scene3d_pipeline
from packages.studio.studio_export import export_studio_glb
from packages.studio.storage import storage_provider
from packages.studio.glb_inspector import GLBInspector
from packages.domain.database import SessionLocal
from packages.domain.models import Base, Tenant, User, Workspace, Project, Scene3DVersion
from uuid import uuid4
import numpy as np


def run_pipeline(filepath: str, export_glb: bool = True):
    print(f"╔{'═'*68}╗")
    print(f"║  VISION 5D — UNIVERSAL CAD UPLOAD                                      ║")
    print(f"╚{'═'*68}╝")
    print(f"  File: {filepath}")

    # 1. Detect format
    info = detect_format(filepath)
    print(f"  Detected: {info.format.value} (method={info.method}, conf={info.confidence:.0%})")
    if info.warnings:
        for w in info.warnings:
            print(f"  ⚠ {w}")

    # 2. Universal ingest
    t0 = time.time()
    geo = ingest_file(filepath)
    print(f"  Import:  {geo.wall_count} walls, {geo.room_count} rooms, {geo.door_count} doors, {geo.window_count} windows")
    print(f"           {geo.importer_used} ({geo.import_duration_ms:.0f}ms)")
    if geo.import_warnings:
        for w in geo.import_warnings:
            print(f"  ⚠ {w}")

    # 3. Generate image for CV pipeline
    try:
        import cv2
        img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
        if geo.walls:
            dw, dh = geo.width, geo.height
            sx = 1200 / max(dw, 1); sy = 800 / max(dh, 1)
            for wall in geo.walls:
                pts = wall["points"]
                for i in range(len(pts) - 1):
                    x1, y1 = int(pts[i][0] * sx), int(pts[i][1] * sy)
                    x2, y2 = int(pts[i+1][0] * sx), int(pts[i+1][1] * sy)
                    cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
        _, buf = cv2.imencode('.png', img)
        img_bytes = buf.tobytes()
    except ImportError:
        img_bytes = b''

    # 4. Plan Understanding
    pid = uuid4()
    p2 = plan_pipeline.process(pid, uuid4(), img_bytes)
    print(f"  Plan:    {p2.graph.room_count()} rooms, {p2.graph.wall_count()} walls ({p2.total_duration_ms:.0f}ms)")

    # 5. Geometry
    p3 = geometry_pipeline.process(pid, phase2_result=p2)
    print(f"  Geometry: {len(p3.stages_completed)} stages, {len(p3.model.floors[0].walls) if p3.model and p3.model.floors else 0} walls ({p3.total_duration_ms:.0f}ms)")

    # 6. 3D Scene
    scene = scene3d_pipeline.process(p3.model)
    stats = scene.scene.statistics if scene.scene else None
    print(f"  3D Scene: {stats.triangle_count if stats else 0} triangles, {stats.mesh_count if stats else 0} meshes")

    if not export_glb:
        print(f"\n  Total: {(time.time()-t0)*1000:.0f}ms")
        return

    # 7. GLB Export
    import json as _j
    scene_json = _j.loads(scene.scene.model_dump_json()) if scene.scene else {}
    glb = export_studio_glb(scene_json, {"draft_data": {"finishes": {"floor_color": "#8B7355"}}})
    glb_hash = hashlib.sha256(glb).hexdigest()
    print(f"  GLB:     {len(glb)} bytes, SHA-256: {glb_hash[:16]}...")

    # 8. Storage
    db = SessionLocal()
    try:
        t = Tenant(id=uuid4(), external_id="upload-" + uuid4().hex[:8])
        db.add(t); db.flush()
        proj = Project(id=uuid4(), workspace_id=uuid4(), tenant_id=t.id, name=os.path.basename(filepath), project_type="imported")
        db.add(proj); db.flush()
        scene_db = Scene3DVersion(id=uuid4(), tenant_id=t.id, project_id=proj.id, version=1, state="COMPLETED", is_complete=True, scene_data=scene_json)
        db.add(scene_db); db.commit()

        art = storage_provider.write_artifact(db, t.id, proj.id, "upload-glb", glb, "model/gltf-binary")
        read = storage_provider.read_artifact(db, art["artifact_id"])
        post_hash = hashlib.sha256(read["data"]).hexdigest() if read and read.get("data") else ""
        hash_ok = glb_hash == post_hash

        insp = GLBInspector(glb)
        print(f"  Storage:  hash_match={hash_ok}, valid={insp.valid}")
        print(f"            {insp.node_count} nodes, {insp.mesh_count} meshes, {insp.material_count} materials")
    finally:
        db.close()

    total = (time.time() - t0) * 1000
    print(f"\n  Total: {total:.0f}ms")
    print(f"  {'✅ PIPELINE COMPLETE' if hash_ok and insp.valid else '⚠️ ISSUES DETECTED'}")

    return {
        "file": filepath, "format": info.format.value,
        "walls": geo.wall_count, "rooms": geo.room_count,
        "glb_size": len(glb), "glb_hash": glb_hash,
        "hash_match": hash_ok, "glb_valid": insp.valid,
        "total_ms": total,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Vision 5D Universal CAD Upload")
    p.add_argument("filepath", help="Path to CAD/BIM/mesh/image file")
    p.add_argument("--detect", action="store_true", help="Detect format only, don't import")
    p.add_argument("--compare", action="store_true", help="Compare heuristic vs production DWG import")
    p.add_argument("--formats", action="store_true", help="List supported formats")
    args = p.parse_args()

    if args.formats:
        print("Supported formats:", ", ".join(supported_formats()))
        sys.exit(0)

    if args.detect:
        info = detect_format(args.filepath)
        print(f"{info.format.value} (method={info.method}, conf={info.confidence:.0%}, ver={info.detected_version})")
        sys.exit(0)

    if args.compare:
        from packages.universal_ingestion.dwg_production import compare_imports
        compare_imports(args.filepath)
        sys.exit(0)

    run_pipeline(args.filepath)
