# Runtime Verification — VISION5D-FULL-PLAN-CODE-QUALITY-AUDIT-001

Every claim below is backed by a real command executed this session (2026-09-11).

## 1. Services

| Check | Command | Result |
|-------|---------|--------|
| API health | curl localhost:8000/health | {"status":"healthy","version":"1.0.0","phase":7,"mode":"production"} |
| API routes | curl openapi.json | 105 paths (v1-v6) |
| Worker | background proc | worker_started worker_id=worker-fc85c553 (running) |
| Dashboard | GET /apps/web/index.html | HTTP 200 |

## 2. GLB Export (E1) — the Phase-1 foundation fix

Executed export_glb() + validate_glb() on a real wall mesh (8 verts, 36 indices, NO precomputed normals):

```
GLB bytes: 1164
valid: True
errors: []
magic OK: True
accessors: 3 | bufferViews: 3 | buffers byteLength: 264
POSITION count: 8 | NORMAL count: 8 | INDEX count: 36
```

Conclusion: the historical F1 bug (empty accessors / NORMAL count 0) is FIXED in current code. Normals are auto-computed when absent. Valid glTF 2.0 produced.

## 3. GLB artifacts on disk

| Artifact | Size | validate_glb |
|----------|------|--------------|
| output/.../RE-SingDetch-FH_AS.glb | 13,160 | False (declared length 13152 != actual 13160) — STALE legacy broken GLB |
| .exports/scene_f467885b...glb | 11,840 | True |
| .exports/50eeb35a...glb | 15,960 | True |
| .exports/probe_scene.glb | 15,960 | True |
| .exports/scene_7f62c0c1...glb | 10,264 | False (14× "NORMAL count 0 != POSITION count 8") — STALE pre-fix |
| .exports/scene_2b2d4271...glb | 212 | False (empty scene, no meshes) — stub |

Conclusion: valid GLBs exist but only for SMALL test scenes. NO valid GLB of the full 1010-wall building exists. Stale broken GLBs remain on disk.

## 4. Scene data

- output/.../exports/RE-SingDetch-FH_AS.v5d = JSON v2.1, 235KB: 1010 walls, 18 rooms, 105 doors, 0 windows. Correct geometry.
- output/.../scene/scene_graph.json = SMALL (17 meshes, 160 vertices, 228 triangles, 6 rooms, 30 furniture) — not the full building.

## 5. DB state (vision5d.db)

36 tables. Real data: projects 106, jobs 500, job_attempts 559, checkpoints 228, progress_events 637, geometry_models 43, geometry_walls 20 (small projects only), scene3d_meshes 34, scene3d_objects 24, scene3d_versions 2, graph_nodes 720, graph_edges 816, understanding_graphs 24, durable_artifact_refs 60, validation_decisions 16, encrypted_credentials 51.

Conclusion: full schema present + operational. But geometry_walls=20 (test projects), NOT the 1010-wall reference building → the reference building was never persisted through the DB pipeline.

## 6. Test suite (regression)

Python 3.14 (authoritative): `pytest tests/` → **170 passed, 0 failed** (219 deprecation warnings).

## 7. Authenticated data flow (frontend→API→DB)

Demo login POST /api/v1/auth/login {provider:google, oauth_token:demo} → sets HttpOnly v5d_session. Then:
- /dashboard/stats → 98 projects, 33 active, 11 AI providers, sync healthy
- /workspaces → 8 workspaces
- /dashboard/pascal-health → operational/LIVE v0.9.2
- /dashboard/activity → 20 items

## 8. NOT runtime-verified (documented, not claimed)

- Full 1010-wall building → mesh gen → valid GLB → Blender render → MP4 tour (D2). Only test scenes (144-160 verts) have been exported/rendered.
- HTML viewer loading a real GLB (F1) — viewer is procedural, so nothing to verify.
