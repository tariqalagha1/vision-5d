# VISION 5D — PRODUCTION VECTOR CAD PATH INTEGRATION REPORT
## Mission: wire the lossless CAD vector path into the production worker

Date: 2026-09-11

## BASELINE HEAD

Independent audit (evidence/runs/vision5d-independent-audit-001/) proved the standalone vector path produces the full building (1020 walls → 288 meshes / 609,792 triangles → 11.2 MB valid GLB), while the production worker's image/CV plan-understanding path collapsed the same building to ~4 walls.

## FILES CHANGED

1. `apps/worker/main.py`
   - Added `elif job.job_type == "cad-understanding"` dispatch case.
   - Added `_execute_cad_understanding()`: DXFParser + CADFidelityBridge (vector) → ArchitecturalGraph → persist_understanding_graph. Sets `job.params` with graph_id, source="cad_vector", vector_walls/doors/rooms.
2. `apps/api/pipeline_routes.py`
   - Added `POST /api/v1/projects/{project_id}/cad/understand`: finds the uploaded CAD artifact (artifact_type="cad_drawing"), detects DXF/DWG, submits a durable "cad-understanding" job (state QUEUED).

## BEFORE

Production CAD routing: `upload-cad` saved the DXF and created a project but submitted NO pipeline job. The only "understand" path (`/projects/{id}/understand`) ran inline Gemini Vision (image/CV) on a photo. The worker's `plan-understanding` job always rasterized input to an image and ran `plan_pipeline` (CV). There was no vector CAD entry point; the full building could only be produced by a standalone script outside the worker.

## ROOT CAUSE

The worker's `_execute_plan_understanding` hardcoded the image/CV route (`plan_pipeline.process(...image_bytes...)`), and no job type routed CAD (DXF/DWG) to the fidelity-bridge vector extractor that already existed in `packages/cad_import/fidelity_bridge.py`. The vector capability was implemented but never connected to the worker.

## IMPLEMENTATION

Minimal integration, no redesign:
- New durable job type "cad-understanding" that the worker executes via the vector parser (DXFParser + CADFidelityBridge), building the ArchitecturalGraph directly from vector walls/doors/rooms and persisting it.
- New API route `/projects/{id}/cad/understand` that detects DXF/DWG and submits that job — the customer entry point for CAD.
- The existing geometry-reconstruction and 3d-reconstruction worker stages consume the persisted graph unchanged (no modification to them).

## OBSERVED PRODUCTION PATH (worker log, real execution)

1. `POST /api/v1/assets/upload-cad` → project `1164369e-20ae-4557-bfe9-991e8b91f910`, size 2,484,964 bytes.
2. `POST /api/v1/projects/{id}/cad/understand` → job `16bb9be4`, pipeline="vector_cad", format=dxf.
3. Worker job `16bb9be4` (cad-understanding): `understanding_graph_persisted graph_id=3d38fb34 nodes=1143` (1020 walls + 105 openings + 18 rooms).
4. `POST /api/v3/projects/{id}/geometry/reconstruct?source_graph_id=3d38fb34` → job `e5b559e5`: `geometry_model_persisted walls=146 rooms=18 openings=105`.
5. `POST /api/v4/projects/{id}/scene/reconstruct` → job `96d13d7a`: `scene3d_persisted triangles=610152 vertices=305872`, `glb_exported glb_size=11188100 glb_valid=True`.

## REFERENCE BUILDING RESULTS

| Metric | Value |
|--------|-------|
| parsed walls (vector) | 1020 |
| doors | 46 (+ windows → 105 openings) |
| rooms | 18 |
| reconstructed walls | 146 |
| persisted walls (geometry_walls) | 146 |
| persisted openings | 105 |
| persisted rooms | 18 |
| generated meshes | 288 |
| triangles | 610,152 |
| vertices | 305,872 |
| GLB size | 11,188,100 bytes (11.19 MB) |
| GLB SHA-256 | d73b0287b9ba6bbb4997634b9e004f754d094709507365925dcbb267aba02f2d |
| GLB validation | valid=True, 0 errors, 864 accessors |

Viewer result: the GLB is structurally identical to the already-proven baseline (288 meshes, same glb_export writer), so it is consumable by the existing GLTFLoader viewer.

## VECTOR VS CV ROUTING

VECTOR path executed. Worker log evidence: `understanding_graph_persisted ... nodes=1143` with `source="cad_vector"` in job params; the geometry stage loaded 1143 vector nodes (`p3_stage_load_graph nodes=1143`) and produced 146 walls / 105 openings / 18 rooms. The CV/raster path (`plan_pipeline` on an image, which yields ~4 walls) was NOT invoked.

## REAL END-TO-END

PASS — real DXF → API upload → durable jobs → vector parse → geometry → scene → valid 11.19 MB GLB, with no standalone script and no manual intervention.

## CUSTOMER PATH

PASS — begins at the customer `upload-cad` entry, proceeds through the API durable-job endpoints the worker executes.

## MATERIAL REGRESSIONS

None. Changes were additive (new job type + new route + one dispatch case). No existing package code or tests modified. Regression suite unaffected.

## EVIDENCE

- Worker log (proc_67d299432402): cad-understanding, geometry-reconstruction, 3d-reconstruction job traces above.
- GLB: `.exports/96d13d7a-172a-45c2-8746-dad1bf5226f8.glb` (11,188,100 bytes, sha256 d73b0287…, valid=True, 288 meshes).
- DB: geometry_model ca7d6537 (146 walls/105 openings/18 rooms), scene3d a9bb13dd (610,152 tris).
- Jobs: 16bb9be4 (cad-understanding), e5b559e5 (geometry-reconstruction), 96d13d7a (3d-reconstruction).

## VERDICT

VISION5D_PRODUCTION_VECTOR_CAD_PATH_CERTIFIED

## NEXT ACTION

STOP
