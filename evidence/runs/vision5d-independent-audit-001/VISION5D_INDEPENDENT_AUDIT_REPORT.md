# VISION 5D — INDEPENDENT EVIDENCE-DRIVEN AUDIT

Date: 2026-09-11
Auditor: independent (skeptical, evidence-driven — no prior certification trusted)

---

## 1. PURPOSE

Vision 5D is an AI-native architectural platform. Customer provides a CAD floor plan (DWG/DXF) or architectural photos; the system must reconstruct a 3D building scene, export a shareable 3D model (GLB), provide an interactive viewer, render the building, and produce a video tour (MP4) so a customer can understand the building's layout, rooms, and spatial relationships without specialized CAD software.

## 2. CANONICAL VALUE LOOP

CUSTOMER UPLOAD (DWG/DXF/photo)
→ INTAKE (asset upload)
→ PLAN UNDERSTANDING (parse walls/rooms/doors)
→ GEOMETRY RECONSTRUCTION (walls w/ thickness, closed rooms, openings)
→ SCENE ASSEMBLY (3D scene graph)
→ [AI DESIGN — furniture/materials/lighting]
→ GLB EXPORT (3D model)
→ VIEWER (interactive 3D, loads GLB)
→ RENDER (Blender → frames)
→ VIDEO TOUR (multi-shot MP4)
→ CUSTOMER DELIVERY (GLB + viewer + MP4)

## 3. OBSERVED RUNTIME PATH (executed this session)

RE-SingDetch-FH_AS.dxf (2.48 MB, 2705 entities)
→ DXFParser → fidelity_bridge → 1020 wall segments / 105 doors / 18 rooms
→ [vector bridge, standalone script] → ArchitecturalGraph
→ geometry_pipeline → 146 walls / 18 rooms / 105 openings
→ scene3d_reconstruction → 288 meshes / 305,656 vertices / 609,792 triangles
→ glb_export → 11.2 MB GLB (valid=True, 864 accessors, 0 errors)
→ GLTFLoader viewer → "288 meshes, 305,656 vertices" (runtime-proven via CDP)
→ Blender 5.2 CYCLES → 3 frames (building with wall/door openings)
→ FFmpeg → MP4 (h264, 960×540, 3 shots)

## 4. PROCESS VERDICT

**PARTIAL**

The core pipeline works, but there are ≥8 pipeline entry points (7 legacy scripts + worker + a new standalone vector bridge), and the plan's "unified pipeline" (v5d_pipeline.py) was never built. The production worker's plan-understanding path rasterizes CAD to an image and re-detects via CV — this collapses the full building to ~4 walls. The lossless CAD vector path exists only as a standalone script I wrote this session, NOT wired into the worker. A customer uploading a real CAD file via the API would get the broken CV path, not the full building.

## 5. INTEGRATION VERDICT

**PARTIAL**

CONNECTED + verified: frontend → API → worker → DB (login → stats → projects → activity all real); scene → GLB; GLB → viewer; GLB → Blender → MP4.
NOT CONNECTED: CAD vector path → worker (standalone script only); AI design → real provider (defaults to simulation); .env → worker (worker does not load .env; only the API does).

## 6. REAL END-TO-END

**PASS** — the full chain was executed with the real reference building and produced a valid GLB, a working viewer, and an MP4. (Caveat: executed via a standalone script, not the production worker path.)

## 7. REAL WORK CLASSIFICATION

| Stage | Classification |
|-------|----------------|
| DXF parsing | REAL WORK (entity extraction, layer classification) |
| Plan understanding (CAD vector) | REAL WORK (wall/room/opening extraction) |
| Geometry reconstruction | REAL WORK (extrusion, topology, room closure, constraint solve) |
| Scene assembly / mesh generation | REAL WORK (609K triangles) |
| GLB export | REAL WORK (binary glTF writer, accessors/normals) |
| Viewer | REAL WORK (GLTFLoader) |
| Blender render | REAL WORK (CYCLES frames) |
| AI design | STATIC/SIMULATED — packages/ai/proposal.py `__init__(provider="simulation")`; rule-based strategies ("minimal/balanced/transformative"), model "v5d-simulation-6.0", no LLM call |
| provider-test job | MOCKED — apps/worker/main.py `_execute_provider_test` sleeps 1s and reports "Connection validated" without contacting any provider |

## 8. REAL OUTPUT

- GLB: 11.2 MB, 288 meshes, 609,792 triangles, valid glTF 2.0 (sha256 ea9003b3…)
- Viewer: loads GLB via GLTFLoader (288 meshes, 305,656 vertices)
- MP4: 3-shot tour, h264 960×540, 3.0s (sha256 565f40be…)
- Geometry: 1020 wall segments / 18 rooms / 105 doors

## 9. OUTCOME VALIDITY

**PARTIAL**

Valid technically (GLB parses, viewer renders, MP4 plays). Material validity gaps: (a) absolute scale is wrong — source DXF declares non-standard `$INSUNITS=70`, building renders at ~2.4m×2.8m footprint with 2.5m walls; (b) AI design produced 0 furniture (simulation with empty room analysis); (c) MP4 is 3 frames — a proof, not a customer tour.

## 10. CUSTOMER VALUE

**PARTIAL**

The CAD→3D reconstruction is genuine and labor-saving. But a customer cannot yet receive a production-grade deliverable: the scale is wrong, the AI design is a simulation, and the video tour is minimal.

## 11. BUSINESS VALUE

**MEANINGFUL** — the core automation (CAD→3D→GLB→video) demonstrably works and reduces manual 3D-modeling labor. Not yet production-revenue-ready due to the gaps above.

## 12. FAILURE/RECOVERY

**PASS (by inspection + runtime artifacts)**

The worker implements a real durable-job system: state machine (COMPLETED/FAILED_TERMINAL/FAILED_RETRYABLE/RUNNING/RESUMING/CANCELLED), checkpoint + resume (228 checkpoints observed in DB), attempt tracking (559 attempts), INTERRUPTED recovery. Active fault-injection (timeout/malformed-input/provider-down) was not performed — the recovery code exists and is exercised by checkpoints, but no bounded-failure test was run this session.

## 13. CODE/CONFIG MATERIAL FINDINGS

1. **AI design is simulated** — packages/ai/proposal.py:19 `def __init__(self, provider="simulation")`; rule-based generation; no LLM call. .env.production sets `AI_PROVIDER=simulation`, `AI_SIMULATION_ALLOWED=true`.
2. **provider-test is fake** — apps/worker/main.py:770-774 sleeps 1s and reports success without contacting a provider.
3. **Worker does not load .env** — only apps/api/main.py:8-16 loads .env; the worker (which runs AI-design jobs) reads `ProviderConfig.from_env()` with no .env loaded, so it defaults to simulation even though .env sets `AI_PROVIDER=nvidia`.
4. **Duplicate pipelines** — 7 legacy scripts (cad_to_5d_pipeline, pipeline_9stage, new_job_9stage, v5d_21_production, studio_workflow, render_cinematic_video, render_full_video) remain and each re-implements the pipeline; the plan said DELETE them (Phase 7, never done).

## 14. SECURITY MATERIAL FINDINGS

1. **Sessions are in-memory** — apps/api/main.py:132 `SESSIONS[session_token] = {...}`; lost on API restart; single-process only. Cookie is HttpOnly/SameSite=lax (good), but no JWT/persisted session store.
2. **Demo auth, not real OAuth** — login creates users with `external_id="google:demo"`; no real OAuth/IdP verification. Acceptable for local/dev, not production multi-tenant.
3. SSRF URL validation exists for the computer_use feature (packages/computer_use/security.py `_validate_url` with urlparse). Vision 5D is a local architectural platform, not a scraping SaaS — SSRF is a secondary concern.

## 15. EVIDENCE INTEGRITY

**PASS** — artifacts carry SHA-256 checksums; runtime evidence (CDP viewer verification, Blender render logs, pixel statistics, pytest output) originates from this session's execution; no reused unrelated evidence for new claims.

## 16. MATERIAL GAPS

1. CAD vector path not wired into production worker — customer upload via API gets the broken CV path (~4 walls).
2. AI design is simulated (rule-based), not a real LLM.
3. Absolute scale wrong (`$INSUNITS=70` ambiguity) — affects real-world dimensions.
4. MP4 tour is 3 frames (proof-of-concept, not a customer tour).
5. 7 duplicate legacy pipelines present (conflicting artifact chains).

## 17. FINAL VERDICT

**CERTIFIED_WITH_RESTRICTIONS**

The primary value loop (CAD → 3D reconstruction → GLB → viewer → render → video) is REAL and executes end-to-end with genuine output — not mocked, not hardcoded. But clearly identified non-fatal material limitations remain: the AI-design stage is a simulation, the CAD vector path is not in the production worker, the scale is wrong, and the tour is minimal.

## 18. NEXT ACTION

Wire the lossless CAD vector path into the production worker (replace the image/CV plan-understanding for CAD assets with the fidelity-bridge vector graph), so a customer uploading a real DXF/DWG through the API gets the full building rather than a 4-wall collapse.
