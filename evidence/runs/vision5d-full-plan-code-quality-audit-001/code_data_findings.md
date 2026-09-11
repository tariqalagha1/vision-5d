# Code / Data / Integration Findings — VISION5D-FULL-PLAN-CODE-QUALITY-AUDIT-001

## 1. HIGH

### H1 — HTML viewers still fabricate geometry instead of loading GLB (F1/F2 from Reset)
- Evidence: cinematic.html (GLTFLoader=0, BoxGeometry+PlaneGeometry=3), studio.html (GLTFLoader=0, procedural=5), generated output/.../cinematic/index.html (BoxGeometry=2, PlaneGeometry=1, no .glb reference). Only 3d-viewer.html has GLTFLoader.
- Plan requirement (stage_contracts S12): "Forbidden: BoxGeometry, PlaneGeometry, procedural anything."
- Root cause: Phase 4 (HTML rewrite) never completed. Consequence chain from Reset §2.3 still applies.
- Impact: the customer-facing viewer shows a fabricated scene, not the actual building.

### H2 — Full 1010-wall building never exported/rendered end-to-end (D2)
- Evidence: every valid GLB is a small test scene; no valid full-building GLB; geometry_walls table = 20 rows (test projects), not 1010.
- Root cause: full pipeline (DXF→geometry→scene→GLB→Blender→MP4) only ever run on toy scenes. Blender verification (V5D-BLENDER-RUNTIME-VERIFICATION-001) used a 1-mesh/144-vert test scene.
- Impact: the plan's core customer deliverable (real building tour) is unproven.

## 2. MEDIUM

### M1 — .v5d binary format not implemented (D1)
- v5d_format.py + mesh_generator.py (Phase 2) absent. .v5d is JSON v2.1 (legacy F4 format reused). Functionally equivalent data, but violates the explicit "binary format with checksum" requirement.

### M2 — Validation/QA packages not built (D5, E2, F2, G2)
- packages/validation = empty __init__. Independent QA pipeline (qa_pipeline.py, glb_validator.py, html_validator.py, video_validator.py) all absent. Only validate_glb() inside glb_export.py exists.

### M3 — Artifact manifest/provenance not built (H1, K1)
- packages/artifacts = empty __init__. No SHA-256 manifest chain (manifest.py absent). .exports has ad-hoc artifacts without a manifest.

### M4 — Duplicate pipelines never deleted (J1)
- All 7 "DELETE" scripts still present: pipeline_9stage.py, cad_to_5d_pipeline.py, new_job_9stage.py, v5d_21_production.py, studio_workflow.py, render_cinematic_video.py, render_full_video.py. Risk of divergent artifact chains persists.

### M5 — Rendering approach deviation (G1)
- Plan: Playwright browser recording. Actual: Blender offline render (verified) + AI photo-tour (cinematic/tour_vision.py, Veo). No ADR documents this decision.

## 3. LOW
- L1: stale broken GLB (13,160 bytes, length mismatch) left in output/ reference dir.
- L2: README stale (describes Phase 1; API is now Phase 7 / 105 routes).
- L3: packages/jobs, packages/observability, packages/hermes_bridge, packages/providers still empty __init__.
- L4: 219 deprecation warnings (datetime.utcnow) — cosmetic.

## 4. Data integrity findings
- No fake/sample data found in the LIVE dashboard path (verified: stats/projects/activity return real DB data).
- No orphan records detected in the tables sampled (jobs/projects/checkpoints counts consistent).
- The 212-byte GLB stubs and 10KB invalid GLBs are STALE artifacts (pre-fix), not live-path mocks — but they are indistinguishable from real outputs by filename, a FAKE_SUCCESS risk if any validation consumes them by existence-check only.

## 5. Integration findings
- FRONTEND → API → WORKER → DB: CONNECTED and verified (login → stats → workspaces → pascal-health → activity).
- API → geometry/scene3d/render routes: present (105 routes) and durable-job driven, but full-building execution unverified.
- SCENE → GLB: FIXED (verified at mesh level), unverified at full-building scale.
- GLB → HTML VIEWER: DISCONNECTED (viewer does not consume GLB).
- GLB → BLENDER → MP4: CONNECTED and verified (test scene).
- BUNDLE/MANIFEST: DISCONNECTED (not built).
