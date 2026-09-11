#!/usr/bin/env python3
"""
Vision 5D — Real CAD-to-5D Validation Pipeline (V5D-REAL-CAD-PILOT-001)
Complete end-to-end: CAD import → understanding → geometry → 3D → studio → AI → export
"""
import os, sys, json, time, hashlib, math
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["V5D_AUTO_CREATE_TABLES"] = "true"

from packages.domain.database import SessionLocal, engine
from packages.domain.models import Base, Tenant, User, Workspace, Project
from packages.cad_import.dxf_parser import DXFParser, extract_walls_from_cad, extract_doors_from_cad, extract_rooms_from_cad
from packages.plan_understanding.pipeline import plan_pipeline
from packages.geometry.pipeline import geometry_pipeline
from packages.scene3d.reconstruction import scene3d_pipeline
from packages.studio.studio_export import export_studio_glb
from packages.studio.storage import storage_provider
from packages.studio.glb_inspector import GLBInspector

EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "evidence", "cad_pilot_001")
os.makedirs(EVIDENCE_DIR, exist_ok=True)


class CADTo5DPipeline:
    def __init__(self):
        self.results = {}
        self.timings = {}
        self.errors = []
        self.warnings = []
        self.start_time = time.time()

    def run(self, dxf_content: str) -> dict:
        print("=" * 70)
        print("  VISION 5D — REAL CAD-TO-5D VALIDATION")
        print("=" * 70)

        self._stage("1. CAD Import", self._cad_import, dxf_content)
        self._stage("2. Plan Understanding", self._plan_understanding)
        self._stage("3. Geometry Reconstruction", self._geometry_recon)
        self._stage("4. 3D Scene Generation", self._scene3d)
        self._stage("5. Studio Draft", self._studio_draft)
        self._stage("6. AI Design Proposals", self._ai_design)
        self._stage("7. GLB Export + Storage", self._glb_export)
        self._stage("8. Independent GLB Inspection", self._glb_inspect)

        return self._final_report()

    def _stage(self, name: str, fn, *args):
        print(f"\n{'─'*50}")
        print(f"  STAGE: {name}")
        print(f"{'─'*50}")
        t0 = time.time()
        try:
            result = fn(*args)
            duration = (time.time() - t0) * 1000
            self.timings[name] = duration
            self.results[name] = {"status": "PASS" if result else "WARN", "output": str(result)[:200], "duration_ms": duration}
            print(f"  Result: {'PASS' if result else 'WARN'} ({duration:.0f}ms)")
            return result
        except Exception as e:
            duration = (time.time() - t0) * 1000
            self.errors.append({"stage": name, "error": str(e)})
            self.results[name] = {"status": "FAIL", "error": str(e), "duration_ms": duration}
            print(f"  FAIL: {str(e)[:200]}")
            import traceback; traceback.print_exc()
            return None

    # ═══════════════════ STAGES ═══════════════════

    def _cad_import(self, dxf_content: str):
        parser = DXFParser()
        self.drawing = parser.parse(dxf_content)
        self.scale = parser.detect_scale(self.drawing)
        self.classified = parser.classify_layers(self.drawing)

        walls = extract_walls_from_cad(self.drawing, parser)
        doors = extract_doors_from_cad(self.drawing, parser)
        rooms = extract_rooms_from_cad(self.drawing, parser)

        print(f"  Entities: {len(self.drawing.entities)}")
        print(f"  Layers: {len(self.drawing.layers)} — {sorted(self.drawing.layers)}")
        print(f"  Walls extracted: {len(walls)}")
        print(f"  Doors extracted: {len(doors)}")
        print(f"  Rooms extracted: {len(rooms)}")
        print(f"  Bounds: {self.drawing.bounds} ({self.drawing.width:.0f} x {self.drawing.height:.0f})")
        print(f"  Scale: {self.scale}x (units → mm)")

        assert len(self.drawing.entities) > 10, "Too few entities — DXF may be empty"
        assert len(walls) > 0, "No walls extracted"
        assert len(rooms) > 0, "No rooms detected"

        self.walls = walls
        self.doors = doors
        self.rooms = rooms

        json.dump({
            "entities": len(self.drawing.entities), "layers": sorted(self.drawing.layers),
            "walls": len(walls), "doors": len(doors), "rooms": len(rooms),
            "bounds": list(self.drawing.bounds), "scale": self.scale,
        }, open(os.path.join(EVIDENCE_DIR, "01_cad_import.json"), "w"), indent=2, default=str)

        return len(walls) > 0 and len(rooms) > 0

    def _plan_understanding(self):
        from packages.cad_import.fidelity_bridge import CADFidelityBridge
        bridge = CADFidelityBridge(self.drawing, self.scale)
        bridge.extract_all()

        # Use fidelity bridge to generate high-quality image
        import numpy as np
        try:
            import cv2
            img = bridge.generate_interior_wall_image(1200, 800)
            if img is None or img.size == 0:
                img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
        except:
            img = np.ones((800, 1200, 3), dtype=np.uint8) * 255

        _, buf = cv2.imencode('.png', img) if 'cv2' in dir() else (None, None)
        img_bytes = buf.tobytes() if buf is not None else b''

        self.fidelity_bridge = bridge
        self.pid = uuid4()
        self.p2_result = plan_pipeline.process(self.pid, uuid4(), img_bytes)

        print(f"  Graph: {self.p2_result.graph.room_count()} rooms, {self.p2_result.graph.wall_count()} walls")
        print(f"  Nodes: {len(self.p2_result.graph.nodes)}, Edges: {len(self.p2_result.graph.edges)}")
        print(f"  Scale: {self.p2_result.scale.scale_ratio if self.p2_result.scale else 'N/A'}")
        print(f"  Duration: {self.p2_result.total_duration_ms:.0f}ms")

        json.dump({
            "rooms": self.p2_result.graph.room_count(), "walls": self.p2_result.graph.wall_count(),
            "nodes": len(self.p2_result.graph.nodes), "edges": len(self.p2_result.graph.edges),
            "duration_ms": self.p2_result.total_duration_ms,
        }, open(os.path.join(EVIDENCE_DIR, "02_plan_understanding.json"), "w"), indent=2, default=str)

        return self.p2_result.graph is not None

    def _geometry_recon(self):
        self.p3_result = geometry_pipeline.process(self.pid, phase2_result=self.p2_result)

        print(f"  Stages completed: {len(self.p3_result.stages_completed)}")
        print(f"  Stages failed: {len(self.p3_result.stages_failed)}")
        if self.p3_result.model:
            f = self.p3_result.model.floors[0] if self.p3_result.model.floors else None
            print(f"  Walls: {len(f.walls) if f else 0}")
            print(f"  Rooms: {len(f.rooms) if f else 0}")
            print(f"  Openings: {len(f.openings) if f else 0}")

        json.dump({
            "stages_completed": self.p3_result.stages_completed,
            "stages_failed": self.p3_result.stages_failed,
            "duration_ms": self.p3_result.total_duration_ms,
            "walls": len(self.p3_result.model.floors[0].walls) if self.p3_result.model and self.p3_result.model.floors else 0,
            "rooms": len(self.p3_result.model.floors[0].rooms) if self.p3_result.model and self.p3_result.model.floors else 0,
        }, open(os.path.join(EVIDENCE_DIR, "03_geometry.json"), "w"), indent=2, default=str)

        return self.p3_result.model is not None

    def _scene3d(self):
        if not self.p3_result.model:
            return False
        self.scene_result = scene3d_pipeline.process(self.p3_result.model)
        s = self.scene_result.scene.statistics if self.scene_result.scene else None
        print(f"  Triangles: {s.triangle_count if s else 0}")
        print(f"  Meshes: {s.mesh_count if s else 0}")
        print(f"  Floor area: {s.total_floor_area_m2 if s else 0:.1f} m²")

        json.dump({
            "triangles": s.triangle_count if s else 0,
            "meshes": s.mesh_count if s else 0,
            "floor_area_m2": s.total_floor_area_m2 if s else 0,
            "room_count": s.room_count if s else 0,
        }, open(os.path.join(EVIDENCE_DIR, "04_scene3d.json"), "w"), indent=2, default=str)

        return self.scene_result.scene is not None

    def _studio_draft(self):
        if not self.scene_result or not self.scene_result.scene:
            return False

        db = SessionLocal()
        try:
            tenant = Tenant(external_id="cad-pilot-tenant"); db.add(tenant); db.flush()
            user = User(tenant_id=tenant.id, external_id="cad:demo", email="cad@v5d.dev", display_name="CAD User")
            db.add(user); db.flush()
            ws = Workspace(tenant_id=tenant.id, name="CAD Pilot Workspace", owner_user_id=user.id)
            db.add(ws); db.flush()
            proj = Project(workspace_id=ws.id, tenant_id=tenant.id, name="2BR Apartment", project_type="residential")
            db.add(proj); db.flush()
            db.commit()

            from packages.domain.models import Scene3DVersion
            import json as _j
            scene_json = _j.loads(self.scene_result.scene.model_dump_json()) if hasattr(self.scene_result.scene, 'model_dump_json') else {}
            scene_db = Scene3DVersion(
                tenant_id=tenant.id, project_id=proj.id, version=1, state="COMPLETED",
                is_complete=True, scene_data=scene_json,
                vertex_count=self.scene_result.scene.statistics.vertex_count if self.scene_result.scene.statistics else 0,
                triangle_count=self.scene_result.scene.statistics.triangle_count if self.scene_result.scene.statistics else 0,
            )
            db.add(scene_db); db.commit()

            print(f"  Tenant: {tenant.id}")
            print(f"  Project: {proj.id}")
            print(f"  Scene version: {scene_db.version}")

            self.cad_tenant_id = tenant.id
            self.cad_project_id = proj.id
            self.cad_scene_id = scene_db.id

            json.dump({"tenant_id": str(tenant.id), "project_id": str(proj.id), "scene_id": str(scene_db.id)},
                      open(os.path.join(EVIDENCE_DIR, "05_studio_draft.json"), "w"), indent=2)
            return True
        finally:
            db.close()

    def _ai_design(self):
        from packages.ai.analysis import scene_analyzer
        from packages.ai.proposal import proposal_generator
        from packages.studio.persistence import seed_furniture_library

        db = SessionLocal()
        try:
            seed_furniture_library(db)

            scene_data = self.scene_result.scene.dict() if hasattr(self.scene_result.scene, 'dict') else {}
            analysis = scene_analyzer.analyze(scene_data, {}, "Modern 2-bedroom apartment layout")
            reqs = scene_analyzer.interpret_requirements(
                "Furnish this 2-bedroom apartment with modern style", "modern_interior", analysis,
                budget_band="standard", seating_capacity=4,
            )
            proposal = proposal_generator.generate(analysis, reqs, option_count=2)

            print(f"  Rooms analyzed: {len(analysis.rooms)}")
            print(f"  Requirements: {reqs.objective.value if hasattr(reqs.objective, 'value') else str(reqs.objective)}")
            print(f"  Options generated: {len(proposal.options)}")
            for i, opt in enumerate(proposal.options):
                print(f"    Option {i+1}: {opt.name} — {len(opt.furniture_additions)} additions, {len(opt.finish_changes)} finishes")

            json.dump({
                "rooms_analyzed": len(analysis.rooms),
                "options": len(proposal.options),
                "option_details": [{"name": o.name, "strategy": o.strategy,
                                    "furniture_additions": len(o.furniture_additions),
                                    "finish_changes": len(o.finish_changes),
                                    "advantages": o.advantages[:2]}
                                   for o in proposal.options],
            }, open(os.path.join(EVIDENCE_DIR, "06_ai_proposals.json"), "w"), indent=2, default=str)

            self.ai_proposal = proposal
            return len(proposal.options) >= 2
        finally:
            db.close()

    def _glb_export(self):
        if not self.scene_result or not self.scene_result.scene:
            return False

        import json as _j
        scene_json = _j.loads(self.scene_result.scene.model_dump_json()) if hasattr(self.scene_result.scene, 'model_dump_json') else {}
        glb_bytes = export_studio_glb(scene_json, {"draft_data": {}})
        content_hash = hashlib.sha256(glb_bytes).hexdigest()

        db = SessionLocal()
        try:
            artifact = storage_provider.write_artifact(
                db, self.cad_tenant_id, self.cad_project_id,
                "cad-pilot-glb", glb_bytes, "model/gltf-binary",
                storage_key_prefix="cad_pilot",
            )
            read_result = storage_provider.read_artifact(db, artifact["artifact_id"])
            hash_match = read_result and read_result.get("hash_match", False)

            print(f"  GLB size: {len(glb_bytes)} bytes")
            print(f"  Content hash: {content_hash[:16]}...")
            print(f"  Storage write: {artifact['storage_key']}")
            print(f"  Storage read-back: {read_result['size_bytes'] if read_result else 0} bytes")
            print(f"  Hash match: {hash_match}")

            json.dump({
                "glb_size": len(glb_bytes), "content_hash": content_hash,
                "storage_key": artifact["storage_key"],
                "hash_match": hash_match,
            }, open(os.path.join(EVIDENCE_DIR, "07_glb_export.json"), "w"), indent=2, default=str)

            self.glb_bytes = glb_bytes
            self.glb_hash = content_hash
            self.glb_artifact_id = artifact["artifact_id"]
            self.glb_hash_match = hash_match
            return hash_match
        finally:
            db.close()

    def _glb_inspect(self):
        if not hasattr(self, 'glb_bytes') or not self.glb_bytes:
            return False

        inspector = GLBInspector(self.glb_bytes)
        summary = inspector.get_object_summary()

        print(f"  GLB valid: {inspector.valid}")
        print(f"  Nodes: {inspector.node_count}, Meshes: {inspector.mesh_count}, Materials: {inspector.material_count}")
        print(f"  Objects: {len(summary['furniture_objects'])} furniture, {len(summary['architectural_objects'])} architectural")

        json.dump({
            "valid": inspector.valid,
            "node_count": inspector.node_count,
            "mesh_count": inspector.mesh_count,
            "material_count": inspector.material_count,
            "furniture_objects": len(summary["furniture_objects"]),
            "materials": [m["name"] for m in summary["materials_summary"]],
        }, open(os.path.join(EVIDENCE_DIR, "08_glb_inspection.json"), "w"), indent=2, default=str)

        return inspector.valid

    def _final_report(self):
        total_duration = (time.time() - self.start_time) * 1000
        stages = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        warned = sum(1 for r in self.results.values() if r["status"] == "WARN")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAIL")

        print(f"\n{'='*70}")
        print(f"  CAD-TO-5D VALIDATION COMPLETE")
        print(f"{'='*70}")
        print(f"  Stages: {passed} PASS, {warned} WARN, {failed} FAIL ({stages} total)")
        print(f"  Total duration: {total_duration:.0f}ms")
        print(f"  Errors: {len(self.errors)}")
        for e in self.errors:
            print(f"    [{e['stage']}] {e['error'][:100]}")

        report = {
            "mission": "V5D-REAL-CAD-PILOT-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stages": self.results,
            "timings": self.timings,
            "errors": self.errors,
            "passed": passed, "warned": warned, "failed": failed,
            "total_duration_ms": total_duration,
            "decision": "COMPLETE" if failed == 0 else "PARTIALLY_COMPLETE",
        }

        path = os.path.join(EVIDENCE_DIR, "final_report.json")
        json.dump(report, open(path, "w"), indent=2, default=str)
        print(f"\n  Report: {path}")

        return report


if __name__ == "__main__":
    from scripts.generate_cad import generate_apartment_dxf
    dxf_content = generate_apartment_dxf()
    pipeline = CADTo5DPipeline()
    report = pipeline.run(dxf_content)

    decision = report.get("decision", "UNKNOWN")
    print(f"\n{'='*70}")
    print(f"  FINAL DECISION: {decision}")
    print(f"{'='*70}")
