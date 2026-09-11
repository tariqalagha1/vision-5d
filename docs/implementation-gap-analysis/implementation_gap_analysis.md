# Implementation Gap Analysis
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

**Authoritative Input**: V5D-ARCHITECTURE-RESET-001.md
**Date**: 2026-07-26
**Repository Size**: 275 files, 87.8 MB, 43,193 Python lines, 78 directories

---

## 1. REPOSITORY AUDIT

### 1.1 Core Packages (18 packages, 24,291 lines)

| # | Package | Lines | Files | Purpose | Reuse? |
|---|---------|-------|-------|---------|--------|
| 1 | `packages/geometry/` | 3,181 | 13 | Wall extrusion, room closure, topology, constraints, validation | **KEEP** — core works correctly |
| 2 | `packages/scene3d/` | 1,810 | 5 | 3D contracts, reconstruction, GLB export, persistence | **MODIFY** — contracts/contracts good, glb_export broken |
| 3 | `packages/cad_import/` | 542 | 2 | DXF parsing, fidelity bridge | **KEEP** — works correctly |
| 4 | `packages/plan_understanding/` | 1,673 | 8 | OCR, wall/room/opening detection, graph building, scale calibration | **KEEP** — works correctly |
| 5 | `packages/ai/` | 1,550 | 6 | Provider client, completion, analysis, proposals | **KEEP** — works correctly |
| 6 | `packages/contracts/` | 717 | 2 | Shared Pydantic models (API-level) | **KEEP** — used by API routes |
| 7 | `packages/domain/` | 1,014 | 4 | SQLAlchemy models, DB config, persistence | **KEEP** — works correctly |
| 8 | `packages/security/` | 239 | 3 | Encryption, production hardening | **KEEP** — works correctly |
| 9 | `packages/studio/` | 1,408 | 6 | GLB inspector, storage, persistence, export orchestration | **MODIFY** — keep inspector/storage, rewrite export |
| 10 | `packages/cinematic/` | 1,398 | 3 | Camera director, storyboard, reveal | **MODIFY** — keep camera paths, rewrite video generation |
| 11 | `packages/universal_ingestion/` | 1,529 | 4 | DWG heuristic, production ingestion, DWG engine | **KEEP** — ingestion foundation |
| 12 | `packages/observability/` | 162 | 1 | Logging, metrics | **KEEP** — works correctly |
| 13 | `packages/artifacts/` | 1 | 1 | Empty init | **BUILD** — will house artifact manifest system |
| 14 | `packages/jobs/` | 1 | 1 | Empty init | **BUILD** — will house job state machine |
| 15 | `packages/providers/` | 1 | 1 | Empty init | **KEEP** — placeholder for future provider system |
| 16 | `packages/hermes_bridge/` | 1 | 1 | Empty init | **KEEP** — placeholder |
| 17 | `packages/validation/` | 1 | 1 | Empty init | **BUILD** — will house independent QA pipeline |
| 18 | `apps/api/` | 2,750 | 7 | FastAPI endpoints (ai, geometry, plan, scene3d, studio) | **KEEP** — API layer works |
| 19 | `apps/worker/` | 998 | 2 | Durable job worker | **KEEP** — job execution works |
| 20 | `apps/web/` | — | 8 (HTML) | Phase 1 console, viewers | **REWRITE** — HTML viewers must use GLTFLoader |

### 1.2 Scripts (24 scripts, 7,173 lines)

| # | Script | Lines | Purpose | Status |
|---|--------|-------|---------|--------|
| 1 | `step01_isolation.py` | 336 | Source isolation + DWG→DXF conversion | **KEEP** — foundational, works correctly |
| 2 | `cad_to_5d_pipeline.py` | 365 | End-to-end pipeline | **DELETE** — duplicate, bypasses packages |
| 3 | `pipeline_9stage.py` | 471 | 9-stage production pipeline | **DELETE** — duplicate, produces broken artifacts |
| 4 | `new_job_9stage.py` | 437 | Another 9-stage variant | **DELETE** — third duplicate pipeline |
| 5 | `render_cinematic_video.py` | 421 | Pillow 2D → MP4 | **DELETE** — replaced by browser recording |
| 6 | `render_full_video.py` | 130 | Another Pillow renderer | **DELETE** — same problem |
| 7 | `production_validation.py` | 339 | Surface-level validation | **REWRITE** — add structural + visual checks |
| 8 | `full_5d_validation.py` | 445 | Comprehensive validation | **REWRITE** — align with new architecture |
| 9 | `certify_p5.py` | 404 | Phase 5 certification | **REWRITE** — check GLB structural validity |
| 10 | `cad_10_validate.py` | 358 | DXF validation | **KEEP** — useful for input verification |
| 11 | `beta_acceptance_rerun.py` | 271 | Acceptance testing | **KEEP** — acceptance test harness |
| 12 | `browser_certify.py` | 261 | Browser validation | **MODIFY** — extend for GLB verification |
| 13 | `delivery_challenge.py` | 298 | Independent verification | **KEEP** — valuable QA tool |
| 14 | `e2e_evidence.py` | 342 | Evidence collection | **KEEP** — evidence recording |
| 15 | `upload_cad.py` | 154 | CAD upload tool | **KEEP** — input ingestion |
| 16 | `studio_workflow.py` | 402 | Studio orchestration | **DELETE** — replaced by unified pipeline |
| 17 | `real_cinematic_integration.py` | 547 | Cinematic integration | **MODIFY** — align with browser recording |
| 18 | `gen_10_rich_dxf.py` | 343 | DXF generation for testing | **KEEP** — test data generator |
| 19 | `generate_cad.py` | 185 | CAD generation | **KEEP** — test utility |
| 20 | `v5d_21_production.py` | 372 | Production run script | **DELETE** — replaced by unified pipeline |
| 21 | `ops_security_test.py` | 74 | Security testing | **KEEP** — security validation |
| 22 | `audit_providers.py` | 67 | Provider audit | **KEEP** — operational tool |
| 23 | `test_provider.py` | 91 | Provider testing | **KEEP** — operational tool |
| 24 | `run_migration.py` | 60 | Migration runner | **KEEP** — DB migration tool |

### 1.3 Infrastructure (9 files)

| File | Purpose | Status |
|------|---------|--------|
| `Dockerfile` | Container build | **KEEP** |
| `docker-compose.yml` (infra) | Service orchestration | **KEEP** |
| `docker-compose.yml` (root) | Dev orchestration | **KEEP** |
| `nginx.conf` | Reverse proxy | **KEEP** |
| `prometheus.yml` | Monitoring | **KEEP** |
| `grafana-dashboard.json` | Dashboard | **KEEP** |
| `deploy.sh` | Deploy script | **KEEP** |
| `docker-entrypoint.sh` | Container entry | **KEEP** |
| `backup.py` | Backup utility | **KEEP** |
| `quality_gate.py` | Quality checks | **MODIFY** |

### 1.4 Tests (3 files, 1,279 lines)

| File | Lines | Scope | Status |
|------|-------|-------|--------|
| `test_integration_v5d.py` | 441 | Integration tests | **EXTEND** — add new pipeline tests |
| `test_phase2.py` | 286 | Plan understanding tests | **KEEP** |
| `test_phase3.py` | 552 | Geometry tests | **KEEP** |

### 1.5 Migrations (3 versions)

| Migration | Purpose | Status |
|-----------|---------|--------|
| `001_initial.py` | Core tables | **KEEP** |
| `002_phase4_scene3d.py` | Scene3D tables | **KEEP** |
| `003_phase5_studio.py` | Studio tables | **KEEP** |

---

## 2. PIPELINE AUDIT

### 2.1 Current Pipelines Identified

| Pipeline | Entry Point | Output | Dependencies | Status |
|----------|-------------|--------|--------------|--------|
| **A: CAD-to-5D** | `cad_to_5d_pipeline.py` | GLB, reports, evidence | packages/cad_import, plan_understanding, geometry, scene3d, studio, ai | **DELETE**: works but uses broken GLB export; duplicate with B and C |
| **B: 9-Stage** | `pipeline_9stage.py` | PNG, GLB, MP4, WebM, GIF | packages/cad_import (partially), then raw Pillow/CV2 | **DELETE**: bypasses most packages, creates procedural geometry, produces broken GLB |
| **C: New Job 9-Stage** | `new_job_9stage.py` | Same as B | Same as B | **DELETE**: third copy of the same broken pipeline |
| **D: Production** | `v5d_21_production.py` | Same as A | Same as A | **DELETE**: fourth entry point into same broken chain |
| **E: Real Cinematic** | `real_cinematic_integration.py` | MP4 via Pillow | packages/cinematic/engine.py | **MODIFY**: keep camera path generation, replace 2D rendering |
| **F: Video Export** | `render_cinematic_video.py` | MP4/WebM via Pillow | None (standalone) | **DELETE**: 2D drawing, not 3D rendering |
| **G: Studio Workflow** | `studio_workflow.py` | GLB export + storage | packages/studio/ | **DELETE**: function absorbed into unified pipeline |
| **H: Step-01** | `step01_isolation.py` | DXF from DWG | LibreDWG | **KEEP**: foundational, works, already in use |

**Net**: 8 pipelines reduced to 2 (Step-01 isolation + unified production pipeline).

### 2.2 Proposed Unified Pipeline

```
PIPELINE: v5d_production.py  (NEW — replaces A, B, C, D, F, G)

Entry: storage/projects/step02-{job_id}/input/RE-SingDetch-FH_AS.dxf
Exit:  storage/projects/step02-{job_id}/delivery/
Stages: 10 (see stage_contracts.md)
Dependencies: ALL packages (no bypassing)
```

---

## 3. AUTHORITATIVE SCENE AUDIT

### 3.1 Options Evaluated

| Criterion | Option A: In-Memory SceneGraph | Option B: Persistent SceneGraph (.v5d) | Option C: GLB as Authoritative |
|-----------|-------------------------------|----------------------------------------|-------------------------------|
| **Performance** | Fastest for single run | Slight serialization overhead (ms) | Slow to parse for modifications |
| **Complexity** | Simplest — no serialization | Medium — format definition needed | High — GLB is read-optimized, not modify-optimized |
| **Debugging** | Hard — lost after process exit | **Easy** — inspect .v5d with tools | Hard — binary GLB, need glTF inspector |
| **Maintainability** | Must regenerate from scratch | **Incremental** — modify and save | Fragile — GLB not designed for in-place edits |
| **Testing** | Hard — need full pipeline run | **Easy** — load .v5d fixture, assert | Medium — need GLB validator |
| **Versioning** | None (ephemeral) | **Monotonic version field** | None — must track by file hash |
| **Recovery** | Must rerun entire pipeline | **Load .v5d from any stage** | Must have all prior stages |
| **Future Features** | Limited — no persistence | **Supports incremental editing** | Limited — GLB is a delivery format |
| **Interoperability** | Python-only | **Binary format, language-agnostic** | **Excellent** — GLB is industry standard |

### 3.2 Recommendation: Option B — Persistent SceneGraph (.v5d)

**Rationale**: The SceneGraph (.v5d) is the authoritative scene. GLB is a DERIVATIVE — an export format, not the source of truth. This follows the same pattern as every professional 3D pipeline (Maya → .mb, Blender → .blend, Unity → .prefab — they all have an internal format that exports to delivery formats).

**Architecture**:
```
SceneGraph (.v5d)  ←── AUTHORITATIVE SOURCE OF TRUTH
    │
    ├──→ GLB export (delivery format, read-only consumer)
    │       │
    │       └──→ HTML viewer (loads GLB, read-only consumer)
    │               │
    │               └──→ Video recorder (captures HTML, read-only consumer)
    │
    └──→ Direct consumers (API, validation, studio)
```

---

## 4. DEPENDENCY AUDIT

### 4.1 Component Dependency Graph

```
                      ┌──────────────────────────────┐
                      │         STEP-01               │
                      │   DWG → LibreDWG → DXF        │
                      │   (foundation, no deps)        │
                      └──────────────┬───────────────┘
                                     │ reads
                                     ▼
                      ┌──────────────────────────────┐
                      │        CAD PARSER             │
                      │   cad_import/dxf_parser.py    │
                      │   Depends: (none)              │
                      │   Consumes: DXF text           │
                      │   Produces: CADDrawing         │
                      └──────────────┬───────────────┘
                                     │ reads
                                     ▼
                      ┌──────────────────────────────┐
                      │    PLAN UNDERSTANDING          │
                      │   plan_understanding/          │
                      │   Depends: cad_import          │
                      │   Consumes: CADDrawing         │
                      │   Produces: ArchGraph          │
                      └──────────────┬───────────────┘
                                     │ reads
                                     ▼
                      ┌──────────────────────────────┐
                      │    GEOMETRY RECONSTRUCTION     │
                      │   geometry/                    │
                      │   Depends: plan_understanding  │
                      │   Consumes: ArchGraph          │
                      │   Produces: GeometryModel      │
                      └──────────────┬───────────────┘
                                     │ reads
                                     ▼
                      ┌──────────────────────────────┐
                      │    SCENE ASSEMBLY              │
                      │   scene3d/reconstruction.py    │
                      │   Depends: geometry, ai        │
                      │   Consumes: GeometryModel,     │
                      │             AI design          │
                      │   Produces: SceneGraph (.v5d)  │
                      └──────┬───────────┬───────────┘
                             │           │ reads
                             │           ▼
                             │  ┌──────────────────────┐
                             │  │    GLB EXPORT         │
                             │  │   scene3d/glb_export  │
                             │  │   Consumes: SceneGraph│
                             │  │   Produces: .glb      │
                             │  └──────────┬───────────┘
                             │             │ reads
                             │             ▼
                             │  ┌──────────────────────┐
                             │  │    HTML VIEWER        │
                             │  │   (template)          │
                             │  │   Consumes: .glb      │
                             │  │   Produces: .html     │
                             │  └──────────┬───────────┘
                             │             │ reads
                             │             ▼
                             │  ┌──────────────────────┐
                             │  │    VIDEO EXPORT       │
                             │  │   (browser record)    │
                             │  │   Consumes: .html     │
                             │  │   Produces: .mp4,.webm│
                             │  └──────────────────────┘
                             │
                             ▼
                      ┌──────────────────────────────┐
                      │    VALIDATION / QA             │
                      │   (read-only, all stages)      │
                      │   Consumes: ALL artifacts      │
                      │   Produces: validation reports │
                      │   NEVER produces: artifacts    │
                      └──────────────────────────────┘
```

### 4.2 Forbidden Dependencies

| Forbidden | Reason |
|-----------|--------|
| HTML → SceneGraph directly | HTML must load GLB, not raw scene data |
| Video → SceneGraph directly | Video must record browser rendering GLB |
| Video → DXF/CADEntities | Video must not parse source files |
| GLB Export → HTML | GLB export must not know about HTML |
| Validation → (write access to artifacts) | Validation is read-only |
| Any stage → any stage more than 1 step ahead | Linear chain only |

### 4.3 Hidden Dependencies (current codebase)

| Hidden Dep | Found In | Risk |
|------------|----------|------|
| `pipeline_9stage.py` imports `cv2` (OpenCV) — not in pyproject.toml | Script | Undocumented dependency |
| `render_cinematic_video.py` imports `PIL` — not in pyproject.toml | Script | Undocumented dependency |
| HTML viewer imports Three.js from CDN (`jsdelivr.net`) | HTML | Internet dependency at runtime |
| `production_validation.py` relies on subprocess `ffprobe` — not declared | Script | System dependency |
| `step01_isolation.py` relies on `dwg2dxf.exe` at `tools/libredwg/` | Script | Platform-specific binary |

### 4.4 Circular Dependencies

**None detected.** The package structure is clean — imports flow inward toward domain/contracts and outward toward API.

---

## 5. OWNERSHIP AUDIT

| Data Structure | Sole Owner | Created During | Mutability | Notes |
|---------------|------------|---------------|------------|-------|
| Walls | SceneGraph (BuildingLevel.walls) | Scene Assembly (Stage 5) | Immutable after creation | Source: wall_ids trace to GeometryModel |
| Doors | SceneGraph (BuildingLevel.doors) | Scene Assembly (Stage 5) | Immutable after creation | Source: opening_ids trace to GeometryModel |
| Windows | SceneGraph (BuildingLevel.windows) | Scene Assembly (Stage 5) | Immutable after creation | Source: opening_ids |
| Rooms | SceneGraph (BuildingLevel.rooms) | Scene Assembly (Stage 5) | Immutable after creation | Source: room_ids trace to GeometryModel |
| Furniture | SceneGraph (BuildingLevel.furniture_instances) | AI Design → Scene Assembly (Stage 6→5) | Mutable until scene frozen | Position/rotation/scale settable in studio |
| Materials | SceneGraph.materials (global) + per-object overrides | Material Assignment (Stage 7) | Mutable until scene frozen | PBR properties |
| Textures | Material.texture_ref (reference) | Material Assignment (Stage 7) | Immutable reference | External image files |
| Lights | SceneGraph.lights | Lighting Setup (Stage 8) | Mutable until scene frozen | Position, intensity, color, type |
| Cameras | SceneGraph.cameras | Scene Assembly (Stage 5) | Camera paths mutable | Default view from bounds |
| Meshes | SceneGraph.building.levels[].meshes | Mesh Generation (Stage 9) | Immutable after generation | Vertices, indices, normals, UVs |
| Metadata | SceneGraph.metadata (dict) | Every stage appends | Append-only | Provenance, stage results, timestamps |
| Validation Results | ValidationReport (separate from scene) | QA stages | Immutable | Never modifies scene |
| Job State | Domain DB (SQLAlchemy) | Job creation | State machine transitions | 17-state worker |
| Artifact Manifest | ArtifactManifest (separate file) | Bundle assembly | Immutable after creation | SHA-256 chain for all files |

**Rule**: No data structure has more than one owner. The SceneGraph OWNS all scene data. Everything else is a derived artifact.

---

## 6. ARTIFACT LIFECYCLE

| Artifact | Created By | Consumed By | Immutable? | Regenerable? | Modifiable? | Deletable? | Gate | Retention |
|----------|-----------|-------------|------------|-------------|-------------|------------|------|-----------|
| DXF (converted) | LibreDWG | DXF Parser | Yes | Yes (from DWG) | No | After pipeline complete | SHA-256 match | Until project archived |
| CADEntities | DXF Parser | Plan Understanding | Yes | Yes | No | No | Entity count check | Pipeline duration |
| ArchGraph | Plan Understanding | Geometry Engine | Yes | Yes | No | No | Scale confidence > 0.5 | Pipeline duration |
| GeometryModel | Geometry Engine | Scene Assembly | Yes | Yes | No | No | Room closure check | Pipeline duration |
| **SceneGraph (.v5d)** | Scene Assembly | GLB Export, QA | **Yes (frozen)** | **Yes** | **No (read-only consumers)** | **No** | Structural validation | **Permanent** |
| GLB (.glb) | GLB Export | HTML, QA | Yes | Yes (from .v5d) | No | Can regenerate | Accessor resolution | Until project archived |
| HTML (.html) | HTML Generator | Browser, QA, Video | Yes | Yes (from GLB template) | No | Can regenerate | GLB loads without errors | Until project archived |
| MP4 (.mp4) | Video Recorder | Customer, QA | Yes | Yes (from HTML) | No | Can regenerate | Frame content check | Until project archived |
| WebM (.webm) | Video Recorder | Customer, QA | Yes | Yes | No | Can regenerate | Same as MP4 | Until project archived |
| GIF (.gif) | Video Recorder | Customer, QA | Yes | Yes | No | Can regenerate | Non-blank frames | Until project archived |
| Thumbnail (.png) | Video Recorder | Customer | Yes | Yes | No | Can regenerate | Exists, non-zero | Until project archived |
| Validation Report | QA Pipeline | Customer, Developer | Yes | No (evidence) | No | No | N/A | Permanent |
| Artifact Manifest | Bundle Assembly | Customer, QA | Yes | No | No | No | All SHA-256s present | Permanent |

---

## 7. STAGE CONTRACTS

### Stage 0: Source Ingestion

| Property | Value |
|----------|-------|
| **Executor** | `step01_isolation.py` |
| **Inputs** | `.dwg` file (from Desktop or upload) |
| **Outputs** | `.dxf` file in `step01-{job_id}/converted/` |
| **Validation** | SHA-256 match of copy, DXF section count, entity count |
| **Failure** | STOP — bad source file |
| **Rollback** | Delete workspace, report error |
| **Retry** | None — fix source file first |

### Stage 1: DXF Parse

| Property | Value |
|----------|-------|
| **Executor** | `packages/cad_import/dxf_parser.py` |
| **Inputs** | DXF text from Stage 0 |
| **Outputs** | `CADDrawing` object (entities, layers, blocks) |
| **Validation** | Entity count > 0, section count = 7 (HEADER, CLASSES, TABLES, BLOCKS, ENTITIES, OBJECTS, THUMBNAILIMAGE) |
| **Failure** | STOP — unparseable DXF |
| **Rollback** | N/A (in-memory) |

### Stage 2: Plan Understanding

| Property | Value |
|----------|-------|
| **Executor** | `packages/plan_understanding/pipeline.py` |
| **Inputs** | `CADDrawing` |
| **Outputs** | `ArchGraph` (walls, rooms, openings, dimensions, scale) |
| **Validation** | Wall count > 0, room count > 0, scale confidence > 0.5 |
| **Failure** | STOP — unrecognizable plan |
| **Rollback** | N/A (in-memory) |

### Stage 3: Geometry Reconstruction

| Property | Value |
|----------|-------|
| **Executor** | `packages/geometry/pipeline.py` |
| **Inputs** | `ArchGraph` |
| **Outputs** | `GeometryModel` (walls with thickness, closed rooms, openings) |
| **Validation** | All walls valid (length > 0), rooms closed, no wall overlaps |
| **Failure** | STOP — geometry cannot be reconstructed |
| **Rollback** | N/A (in-memory) |

### Stage 4: AI Design

| Property | Value |
|----------|-------|
| **Executor** | `packages/ai/` (provider_client, analysis, proposal) |
| **Inputs** | `GeometryModel` (room names, dimensions, functions) |
| **Outputs** | Furniture placement plan, material palette, lighting plan |
| **Validation** | Furniture count > 0, all rooms furnished, no collisions |
| **Failure** | CONTINUE with defaults — AI is advisory |
| **Rollback** | Use default furniture layout |

### Stage 5: Scene Assembly

| Property | Value |
|----------|-------|
| **Executor** | `packages/scene3d/reconstruction.py` |
| **Inputs** | `GeometryModel` + AI design output |
| **Outputs** | `SceneGraph` (.v5d file) |
| **Validation** | Wall count matches GeometryModel, room count matches, all objects have valid UUIDs, material count > 0 |
| **Failure** | STOP — authoritative scene cannot be assembled |
| **Rollback** | Delete .v5d, report error |
| **Recovery** | Regenerate from GeometryModel |

### Stage 6: Mesh Generation

| Property | Value |
|----------|-------|
| **Executor** | Mesh triangulator (NEW — part of scene3d) |
| **Inputs** | `SceneGraph` (.v5d) |
| **Outputs** | Updated `SceneGraph` with `MeshData[]` populated |
| **Validation** | All meshes have vertices > 0, indices > 0, triangles > 0, valid bboxes |
| **Failure** | STOP — cannot generate meshes |
| **Rollback** | Revert to pre-mesh SceneGraph |

### Stage 7: Material Assignment

| Property | Value |
|----------|-------|
| **Executor** | Material library + assignment (NEW) |
| **Inputs** | `SceneGraph` (.v5d) |
| **Outputs** | Updated `SceneGraph` with materials assigned to all meshes |
| **Validation** | Every mesh has material_id, material count > 0, PBR properties valid |
| **Failure** | CONTINUE with defaults |

### Stage 8: Lighting Setup

| Property | Value |
|----------|-------|
| **Executor** | Light placer (NEW) |
| **Inputs** | `SceneGraph` (.v5d) |
| **Outputs** | Updated `SceneGraph` with lights configured |
| **Validation** | At least 1 ambient + 1 directional light, no light inside walls |
| **Failure** | CONTINUE with defaults |

### Stage 9: SceneGraph Validation

| Property | Value |
|----------|-------|
| **Executor** | SceneGraph validator (NEW — internal) |
| **Inputs** | `SceneGraph` (.v5d) |
| **Outputs** | Validation report (blocking/review/advisory) |
| **Validation** | Zero blocking issues |
| **Failure** | STOP if blocking; WARN if review; OK if advisory |
| **Stop condition** | Blocking issues: missing geometry, zero meshes, zero materials |

### Stage 10: GLB Export

| Property | Value |
|----------|-------|
| **Executor** | `packages/scene3d/glb_export.py` (FIXED) |
| **Inputs** | `SceneGraph` (.v5d) — ONLY |
| **Outputs** | Valid `.glb` file |
| **Validation** | All accessors resolve, all bufferViews populated, GLB opens in GLTFValidator, all meshes visible |
| **Failure** | STOP — GLB is the primary deliverable |
| **Rollback** | Delete GLB, fix SceneGraph, re-export |

### Stage 11: GLB Validation (Independent QA)

| Property | Value |
|----------|-------|
| **Executor** | QA pipeline (NEW — read-only) |
| **Inputs** | `.glb` file |
| **Outputs** | QA report (NEVER modifies GLB) |
| **Validation** | Opens in headless Three.js, node count matches SceneGraph, mesh count matches, screenshot captured |
| **Failure** | STOP with evidence |

### Stage 12: HTML Viewer

| Property | Value |
|----------|-------|
| **Executor** | HTML template renderer (NEW) |
| **Inputs** | `.glb` file + camera paths from SceneGraph |
| **Outputs** | `index.html` with embedded GLBLoader, camera controls, overlays |
| **Validation** | Loads GLB without console errors, scene node count matches, NO procedural geometry |
| **Failure** | STOP |

### Stage 13: HTML Validation

| Property | Value |
|----------|-------|
| **Executor** | Browser validator (NEW) |
| **Inputs** | `index.html` |
| **Outputs** | Screenshot, console log, node count report |
| **Validation** | GLB URL resolves, scene renders, no missing textures, object count matches |
| **Failure** | STOP with evidence |

### Stage 14: Video Recording

| Property | Value |
|----------|-------|
| **Executor** | Browser recorder (NEW — Playwright) |
| **Inputs** | `index.html` |
| **Outputs** | `.mp4` (H.264), `.webm` (VP9), `.gif`, `.png` thumbnail |
| **Validation** | Frame content non-blank, camera motion detectable, perceptual hash diversity > 5 unique frames |
| **Failure** | STOP — video is primary customer deliverable |

### Stage 15: Video Validation

| Property | Value |
|----------|-------|
| **Executor** | Video QA (NEW) |
| **Inputs** | `.mp4`, `.webm`, `.gif` |
| **Outputs** | Frame analysis, GLB-to-video match report |
| **Validation** | Extract frames at 10 checkpoints, verify non-blank, compare to GLB render |
| **Failure** | STOP with frame evidence |

### Stage 16: Bundle Assembly

| Property | Value |
|----------|-------|
| **Executor** | Artifact bundler (NEW) |
| **Inputs** | All validated artifacts from Stages 10-15 |
| **Outputs** | Delivery directory with manifest, all files, SHA-256 chain |
| **Validation** | All files exist, all SHAs match manifest, total size reasonable |
| **Failure** | STOP — cannot deliver incomplete bundle |

---

## 8. IMPLEMENTATION PHASES

### Phase 1: GLB Export Fix (P0 — Foundation)
**Depends on**: Nothing  
**Duration**: 1-2 days  
**Files**: `packages/scene3d/glb_export.py`  
**Changes**: ~30 lines modified  
**Tests**: Verify GLB opens in GLTFValidator, all accessors resolve, meshes are visible  
**Independent**: Yes — can be tested with existing Scene3D objects  

### Phase 2: SceneGraph Serialization (P0 — Foundation)
**Depends on**: Phase 0 (existing contracts)  
**Duration**: 2 days  
**Files**: NEW `packages/scene3d/scene_graph.py`, NEW `packages/scene3d/v5d_format.py`  
**Changes**: ~500 new lines  
**Tests**: Round-trip serialize/deserialize, versioning, hash integrity  
**Independent**: Yes — testable with sample scene data  

### Phase 3: Unified Pipeline (P0 — Foundation)
**Depends on**: Phase 1, Phase 2  
**Duration**: 2 days  
**Files**: NEW `scripts/v5d_pipeline.py`, modify `apps/worker/main.py`  
**Changes**: ~400 new lines, ~200 modified  
**Tests**: Full pipeline run with sample DXF, verify all stage outputs  
**Independent**: Yes — end-to-end testable  

### Phase 4: HTML Viewer Rewrite (P0 — Customer-facing)
**Depends on**: Phase 1 (valid GLB needed)  
**Duration**: 1 day  
**Files**: Rewrite `apps/web/cinematic.html` as template  
**Changes**: ~200 modified lines  
**Tests**: Load GLB, verify node count, verify no BoxGeometry  
**Independent**: Yes — testable with any valid GLB  

### Phase 5: Browser Video Recording (P0 — Customer-facing)
**Depends on**: Phase 3, Phase 4  
**Duration**: 2 days  
**Files**: NEW `scripts/v5d_video_export.py`  
**Changes**: ~300 new lines  
**Tests**: Record browser, verify frames non-blank, compare to GLB render  
**Independent**: Partially — needs Phase 4 HTML, but testable with any HTML+GLB  

### Phase 6: Validation Hardening (P1 — Quality)
**Depends on**: Phase 1  
**Duration**: 1 day  
**Files**: Rewrite `scripts/production_validation.py`, NEW `packages/validation/`  
**Changes**: ~500 new + modified lines  
**Tests**: Run against known-good and known-bad GLBs  
**Independent**: Yes  

### Phase 7: Cleanup and Migration (P1 — Hygiene)
**Depends on**: Phase 3  
**Duration**: 1 day  
**Files**: DELETE 8 scripts, reorganize 3 directories  
**Changes**: ~8,000 lines deleted  
**Tests**: Verify deleted files not imported anywhere  
**Independent**: Yes  

---

## 9. COMPONENT STATUS MATRIX

| Component | Current Status | Target Status | Reuse % | Rewrite % | Delete % | Risk | Effort |
|-----------|---------------|---------------|---------|-----------|----------|------|--------|
| `packages/geometry/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/scene3d/contracts.py` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/scene3d/reconstruction.py` | Working | Keep | 95% | 5% | 0% | Low | 1h |
| `packages/scene3d/glb_export.py` | **BROKEN** | Rewrite core | 40% | 60% | 0% | **HIGH** | 2d |
| `packages/scene3d/persistence.py` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/cad_import/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/plan_understanding/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/ai/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/contracts/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/domain/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/security/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/studio/` | Working | Modify | 70% | 30% | 0% | Medium | 1d |
| `packages/cinematic/` | Working | Modify | 80% | 20% | 0% | Medium | 1d |
| `packages/universal_ingestion/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/observability/` | Working | Keep | 100% | 0% | 0% | Low | None |
| `packages/artifacts/` | Empty init | Build | 0% | 0% | 0% | Low | 4h |
| `packages/jobs/` | Empty init | Build | 0% | 0% | 0% | Low | 4h |
| `packages/validation/` | Empty init | Build | 0% | 0% | 0% | Medium | 1d |
| `apps/api/` | Working | Keep | 95% | 5% | 0% | Low | 2h |
| `apps/worker/` | Working | Keep | 95% | 5% | 0% | Low | 2h |
| `apps/web/*.html` | **DISCONNECTED** | Rewrite | 20% | 80% | 0% | **HIGH** | 1d |
| `scripts/step01_isolation.py` | Working | Keep | 100% | 0% | 0% | Low | None |
| `scripts/production_validation.py` | Shallow | Rewrite | 20% | 80% | 0% | Medium | 1d |
| `scripts/cad_to_5d_pipeline.py` | Duplicate | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/pipeline_9stage.py` | Duplicate | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/new_job_9stage.py` | Duplicate | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/v5d_21_production.py` | Duplicate | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/studio_workflow.py` | Duplicate | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/render_cinematic_video.py` | 2D broken | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/render_full_video.py` | 2D broken | **DELETE** | 0% | 0% | 100% | Low | None |
| `scripts/real_cinematic_integration.py` | 2D | Modify | 60% | 40% | 0% | Medium | 4h |
| `scripts/certify_p5.py` | Shallow | Rewrite | 30% | 70% | 0% | Medium | 4h |
| `scripts/full_5d_validation.py` | Shallow | Rewrite | 30% | 70% | 0% | Medium | 4h |
| `scripts/delivery_challenge.py` | Working | Keep | 100% | 0% | 0% | Low | None |
| `tests/` | Sparse | Extend | 70% | 30% | 0% | Medium | 2d |

---

## 10. CODE CHANGE INVENTORY

### Files to KEEP (unchanged): 23 files
```
packages/geometry/*.py           (13 files, 3,181 lines)
packages/cad_import/*.py         (2 files, 542 lines)
packages/plan_understanding/*.py (8 files, 1,673 lines)
packages/ai/*.py                 (6 files, 1,550 lines)
packages/contracts/models.py     (1 file, 716 lines)
packages/domain/*.py             (4 files, 1,014 lines)
packages/security/*.py           (3 files, 239 lines)
packages/universal_ingestion/*.py(4 files, 1,529 lines)
packages/observability/__init__.py (1 file, 162 lines)
scripts/step01_isolation.py      (1 file, 336 lines)
scripts/delivery_challenge.py    (1 file, 298 lines)
scripts/cad_10_validate.py       (1 file, 358 lines)
scripts/beta_acceptance_rerun.py (1 file, 271 lines)
scripts/e2e_evidence.py          (1 file, 342 lines)
scripts/browser_certify.py       (1 file, 261 lines)
apps/api/*.py                    (7 files, 2,750 lines)
apps/worker/main.py              (1 file, 998 lines)
migrations/versions/*.py         (3 files, 647 lines)
tests/test_phase2.py             (1 file, 286 lines)
tests/test_phase3.py             (1 file, 552 lines)
```
**Total unchanged: ~17,300 lines**

### Files to MODIFY: 11 files

| File | Changes | Lines Changed | Effort |
|------|---------|--------------|--------|
| `packages/scene3d/glb_export.py` | Fix accessor/bufferView population | ~30 lines | 2d |
| `packages/scene3d/reconstruction.py` | Add SceneGraph serialization hook | ~50 lines | 2h |
| `packages/studio/studio_export.py` | Consume SceneGraph, not raw data | ~100 lines | 4h |
| `packages/cinematic/engine.py` | Feed camera paths to SceneGraph | ~40 lines | 2h |
| `scripts/production_validation.py` | Add structural + visual checks | ~200 lines | 1d |
| `scripts/certify_p5.py` | Align with new stages | ~150 lines | 4h |
| `scripts/full_5d_validation.py` | Align with new stages | ~150 lines | 4h |
| `scripts/real_cinematic_integration.py` | Use browser recording | ~200 lines | 4h |
| `apps/web/cinematic.html` | Use GLTFLoader | ~200 lines | 1d |
| `apps/web/index.html` | Use GLTFLoader | ~200 lines | 4h |
| `infrastructure/quality_gate.py` | Add GLB validity check | ~30 lines | 1h |
**Total modified: ~1,350 lines**

### Files to DELETE: 11 files

```
scripts/cad_to_5d_pipeline.py         (365 lines)
scripts/pipeline_9stage.py            (471 lines)
scripts/new_job_9stage.py             (437 lines)
scripts/v5d_21_production.py          (372 lines)
scripts/studio_workflow.py            (402 lines)
scripts/render_cinematic_video.py     (421 lines)
scripts/render_full_video.py          (130 lines)
apps/web/3d-viewer.html               (procedural viewer)
apps/web/cinematic_luxury.html        (procedural viewer)
apps/web/cinematic_v2.html            (procedural viewer)
apps/web/geometry-editor.html         (procedural viewer)
```
**Total deleted: ~2,600 lines + 4 HTML files**

### Files to CREATE: 7 files

| File | Purpose | Estimated Lines |
|------|---------|----------------|
| `packages/scene3d/v5d_format.py` | SceneGraph binary serialization | ~400 |
| `packages/scene3d/mesh_generator.py` | Triangulation from semantic objects | ~300 |
| `packages/validation/qa_pipeline.py` | Read-only independent QA | ~400 |
| `packages/artifacts/manifest.py` | Artifact manifest system | ~200 |
| `packages/jobs/state_machine.py` | Job state management | ~300 |
| `scripts/v5d_pipeline.py` | Unified production pipeline | ~500 |
| `scripts/v5d_video_export.py` | Browser recording → video | ~300 |
**Total new: ~2,400 lines**

### Directories to Reorganize

| Change | Reason |
|--------|--------|
| `output/RE-SingDetch-FH_AS/` → archive | Old broken artifacts |
| `storage/projects/pipeline-9-stage/` → archive | Old pipeline output |
| `storage/projects/job-6ab2448e5aa7/` → archive | Old job output |

### Net Change Summary

| Category | Count |
|----------|-------|
| Files kept (unchanged) | 23 |
| Files modified | 11 |
| Files deleted | 11 |
| Files created | 7 |
| Lines unchanged | ~17,300 |
| Lines modified | ~1,350 |
| Lines deleted | ~2,600 |
| Lines created | ~2,400 |
| **Net code change** | **~-200 lines** (fewer lines, better architecture) |

---

## 11. RISK ANALYSIS

| # | Risk | Likelihood | Impact | Mitigation | Recovery |
|---|------|-----------|--------|------------|----------|
| R1 | Fixed GLB export still produces invalid GLB | Low | **High** | Validate with GLTFValidator + headless Three.js before commit | Revert to known-good GLB export test fixture |
| R2 | Playwright not available on target system | Medium | High | Abstract browser backend, support Playwright + Puppeteer + headless Chrome CDP | Fallback to Puppeteer |
| R3 | SceneGraph format migration breaks existing data | Low | High | Versioned format, backward-compatible reader, migration script for old .v5d files | Roll back format, fix reader |
| R4 | Browser rendering non-deterministic (frame hashes differ) | Medium | Medium | Fixed random seed, fixed camera paths, hash comparison with Hamming tolerance | Increase tolerance, use perceptual hash |
| R5 | HTML viewer fails to load GLB from file:// URL | Medium | Medium | Test with both file:// and http://, use relative paths | Host via local server if needed |
| R6 | Existing DXF files incompatible with new pipeline | Low | Low | New pipeline uses same DXF parser (cad_import) — no format change | N/A |
| R7 | Third-party GLTFLoader version breaks | Low | Medium | Pin Three.js version in HTML template, test with CI | Revert to known-good version |
| R8 | Performance regression in unified pipeline | Low | Low | Pipeline is linear, each stage is already optimized | Profile and optimize bottleneck |
| R9 | Undiscovered hidden dependencies break | Medium | Medium | Full dependency audit above, declare all deps in pyproject.toml | Add missing dep, rebuild |
| R10 | Video encoding fails in CI (no GPU) | Medium | Low | Use software encoding (libx264), pre-render to PNG frames | Pre-render frames, encode separately |

---

## 12. IMPLEMENTATION ORDER

```
PHASE 1: FOUNDATION — GLB Export Fix                 [2 days]
  ├── Task 1.1: Fix glb_export.py accessor population
  ├── Task 1.2: Add GLB validation (opens in GLTFValidator)
  └── Task 1.3: Test with sample Scene3D data

PHASE 2: FOUNDATION — SceneGraph Serialization        [2 days]
  ├── Task 2.1: Define .v5d binary format spec
  ├── Task 2.2: Implement v5d_format.py (serialize/deserialize)
  └── Task 2.3: Implement mesh_generator.py

PHASE 3: FOUNDATION — Unified Pipeline                [2 days]
  ├── Task 3.1: Create v5d_pipeline.py (10 stages)
  ├── Task 3.2: Add per-stage approval gates
  ├── Task 3.3: Add SHA-256 provenance chain
  └── Task 3.4: End-to-end test with step02 DXF

PHASE 4: DELIVERY — HTML Viewer Rewrite               [1 day]
  ├── Task 4.1: Create GLTFLoader-based template
  ├── Task 4.2: Embed camera paths from SceneGraph
  ├── Task 4.3: Test with pipeline GLB output
  └── Task 4.4: Verify no BoxGeometry in output

PHASE 5: DELIVERY — Browser Video Recording           [2 days]
  ├── Task 5.1: Implement Playwright browser control
  ├── Task 5.2: Frame capture pipeline
  ├── Task 5.3: FFmpeg encoding (MP4, WebM, GIF)
  └── Task 5.4: End-to-end video verification

PHASE 6: QUALITY — Validation Hardening               [1 day]
  ├── Task 6.1: Rewrite production_validation.py
  ├── Task 6.2: Implement QA pipeline (read-only)
  ├── Task 6.3: Add visual checks (screenshots)
  └── Task 6.4: Run against known-bad artifacts

PHASE 7: HYGIENE — Cleanup                            [1 day]
  ├── Task 7.1: Delete 8 duplicate scripts
  ├── Task 7.2: Delete 4 procedural HTML viewers
  ├── Task 7.3: Archive old job/storage directories
  └── Task 7.4: Update pyproject.toml dependencies
```

**Total: 11 days (7 phases, each independent and mergeable)**

---

## 13. MIGRATION READINESS

### Pre-Migration Checklist

- [ ] Architecture document approved (V5D-ARCHITECTURE-RESET-001)
- [ ] Gap analysis reviewed (this document)
- [ ] All stakeholders aligned on "one scene" principle
- [ ] Test DXF available at `storage/projects/step02-e135eab76a86/input/`
- [ ] LibreDWG 0.13.3 confirmed working
- [ ] Playwright or Puppeteer selected and tested
- [ ] GLTFValidator integrated into CI

### Migration Readiness Score: 7/10

**Ready**: Source material exists. Packages are solid. Architecture is clear.
**Not ready**: GLB export fix not yet implemented. Browser recording not yet tested.
**Risk**: LOW — each phase is independent and reversible. Old artifacts preserved in archive.

---

## 14. FINAL SUMMARY

```
IMPLEMENTATION GAP ANALYSIS COMPLETE

1. Components to KEEP:      23 files  (~17,300 lines) — geometry, parsing, AI, contracts, domain, security
2. Components to REWRITE:    5 files  (~1,350 lines)  — glb_export, HTML viewers, validation scripts
3. Components to DELETE:    11 files  (~2,600 lines)  — duplicate pipelines, 2D renderers, procedural viewers
4. Components to BUILD:      7 files  (~2,400 lines)  — v5d format, mesh gen, unified pipeline, browser recorder, QA
5. Authoritative Scene:      Persistent SceneGraph (.v5d binary format) — NOT GLB, NOT in-memory, NOT JSON
6. Total Phases:             7 phases, each independently mergeable and testable
7. Highest-Risk:             Phase 1 (GLB export fix) — foundation for everything else
8. Estimated Effort:         11 days (full-time)
9. Migration Readiness:      7/10 — ready to begin Phase 1 immediately
```
