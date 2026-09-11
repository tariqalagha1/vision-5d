# Plan → Implementation Traceability Matrix
## VISION5D-FULL-PLAN-CODE-QUALITY-AUDIT-001

Status legend: IV=IMPLEMENTED_AND_VERIFIED, INV=IMPLEMENTED_NOT_RUNTIME_VERIFIED, PART=PARTIALLY_IMPLEMENTED, DISC=IMPLEMENTED_BUT_DISCONNECTED, MISS=MISSING_IMPLEMENTATION, DEVIATION=implemented via different approach.

| ID | Planned Requirement | Authority | Expected | Actual | Status | Runtime Verified | Gap | Severity |
|----|--------------------|-----------|----------|--------|--------|------------------|-----|----------|
| A1 | DWG→DXF ingestion | Reset §3.4 Step01; stage_contracts S0 | step01_isolation.py + LibreDWG | step01_isolation.py present; converted.dxf exists | IV | Yes (converted.dxf 2.4MB) | — | — |
| A2 | DXF parse → entities | stage_contracts S1 | cad_import/dxf_parser.py | cad_import/dxf_parser.py (DXFParser, extract_walls/doors/rooms) | IV | Yes (geometry derived from it) | — | — |
| B1 | Plan understanding → ArchGraph | stage_contracts S2 | plan_understanding/ | plan_understanding/ (8 files: ocr, detection, graph, understanding, pipeline) | IV | Yes (graph_nodes 720, graph_edges 816 in DB) | — | — |
| B2 | Geometry reconstruction | stage_contracts S3 | geometry/pipeline.py → GeometryModel | geometry/ (11 files); 1010 walls / 18 rooms / 105 doors in .v5d | IV | Yes (.v5d JSON v2.1) | — | — |
| C1 | AI design (furniture/materials/lighting) | stage_contracts S4 | packages/ai/ | ai/ (6 files) + ai_design.v5d.json (30 furniture) | IV | Yes | — | — |
| D1 | SceneGraph .v5d authoritative scene | Reset §3.2, gap_analysis Phase 2 | **Binary** .v5d (magic/JSON/BIN/checksum) | .v5d is **JSON v2.1** (235KB); no v5d_format.py | PART | — | Binary format not implemented (F4 legacy JSON reused) | MEDIUM |
| D2 | Mesh generation (wall/floor/ceil/door/window/roof) | stage_contracts S6 | scene3d/mesh_generator.py | Mesh gen inside scene3d/reconstruction.py (_make_*_mesh); no separate mesh_generator.py | INV | Not at full scale (only 160-vert test scenes) | Full 1010-wall mesh→GLB never executed | HIGH |
| D3 | Material assignment | stage_contracts S7 | material library | _default_materials() in reconstruction.py | IV | Yes (materials in GLB) | — | — |
| D4 | Lighting setup | stage_contracts S8 | light placer | _default_lights() (ambient + directional) | IV | Yes | — | — |
| D5 | SceneGraph validation | stage_contracts S9 | packages/validation/scene_validator.py | _validate_scene() in reconstruction.py; packages/validation = empty __init__ | PART | — | Dedicated validation package not built | MEDIUM |
| E1 | GLB export (accessors populated) | gap_analysis Phase 1 | scene3d/glb_export.py FIXED | FIXED — accessors/bufferViews/byteLength injected; auto flat normals | IV | **Yes** (runtime: valid GLB, 3 accessors, NORMAL count == POSITION count) | — | — |
| E2 | Independent GLB validation | stage_contracts S11 | packages/validation/glb_validator.py | validate_glb() inside glb_export.py (not independent QA) | INV | Yes (validate_glb works) | No independent QA pipeline | MEDIUM |
| F1 | HTML viewer loads GLB (GLTFLoader) | stage_contracts S12 ("Forbidden: BoxGeometry/PlaneGeometry/procedural") | GLTFLoader-based viewer | cinematic.html, studio.html, generated index.html still procedural (BoxGeometry/PlaneGeometry); only 3d-viewer.html has GLTFLoader | MISS | — | F2 from Reset UNRESOLVED — viewer fabricates geometry | **HIGH** |
| F2 | HTML validation | stage_contracts S13 | html_validator.py | html_validation.json exists (legacy); no validator package | PART | — | — | MEDIUM |
| G1 | Video recording → MP4/WebM/GIF | stage_contracts S14 | Playwright browser record | **Blender offline render** (rendering/blender_scene_builder.py) + FFmpeg; photo_tour via cinematic/tour_vision.py | IV (DEVIATION) | Yes (Blender 30-frame MP4 verified; photo_tour.mp4 15MB) | Playwright→Blender deviation, no ADR | MEDIUM |
| G2 | Video validation | stage_contracts S15 | video_validator.py | video_validation.json (legacy); no validator package | PART | — | — | MEDIUM |
| H1 | Customer bundle + manifest + SHA-256 | stage_contracts S16 | packages/artifacts/manifest.py | packages/artifacts = empty __init__; .exports has ad-hoc artifacts, no manifest chain | PART | — | Manifest/provenance system not built | MEDIUM |
| I1 | API layer | gap_analysis (apps/api KEEP) | FastAPI endpoints | 105 routes across v1-v6 | IV | Yes (openapi.json 105 paths) | — | — |
| I2 | Durable worker | gap_analysis (apps/worker KEEP) | 17-state job worker | apps/worker/main.py; 500 jobs, 559 attempts, 228 checkpoints in DB | IV | Yes (worker running) | — | — |
| I3 | DB schema + persistence | gap_analysis (domain KEEP) | SQLAlchemy models + migrations | 36 tables (geometry_*, scene3d_*, understanding_graphs, checkpoints, durable_artifact_refs, validation_decisions, etc.) | IV | Yes (106 projects, 500 jobs) | — | — |
| I4 | Frontend dashboard | gap_analysis (apps/web REWRITE) | console + viewers | dashboard works (98 projects, stats, health, activity) | IV | Yes (verified this session) | — | — |
| I5 | Frontend↔backend integration | Reset §6 | connected | dashboard → API → worker → DB all connected | IV | Yes (login→stats→workspaces→pascal-health→activity all real) | — | — |
| J1 | Cleanup (delete 8 dup scripts + 4 procedural viewers) | gap_analysis Phase 7 | DELETE pipeline_9stage.py, cad_to_5d_pipeline.py, new_job_9stage.py, v5d_21_production.py, studio_workflow.py, render_cinematic_video.py, render_full_video.py + 4 procedural HTML | All still present | MISS | — | Duplicate pipelines remain; risk of divergent artifacts | MEDIUM |
| K1 | Provenance / SHA-256 chain | Reset §3.4 Steps + stage_contracts S16 | per-stage input→output SHA-256 | .v5d has source sha256; no full chain manifest | PART | — | — | LOW |

## Summary
- Implemented & runtime-verified (IV): 14
- Implemented, not runtime-verified at scale (INV): 2
- Partially implemented (PART): 6
- Missing (MISS): 2
- Deviations (documented, not defects): 1 (G1 Blender)
- Total: 24

Material gaps (HIGH + MEDIUM that affect plan conformance): F1 (HIGH), D2 (HIGH), D1/D5/E2/F2/G2/H1/J1 (MEDIUM) = 8 gaps.
