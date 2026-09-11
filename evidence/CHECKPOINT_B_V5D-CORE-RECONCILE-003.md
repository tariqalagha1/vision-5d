# Vision 5D — Architecture Checkpoint B
## V5D-CORE-RECONCILE-003
### Repository-Grounded Architecture Review

**Date:** 2026-07-23
**Reviewer:** Hermes Architecture Audit
**Evidence Source:** Full repository scan (7,870 lines across 36 files)

---

## 1. EXECUTIVE VERDICT

**DECISION B — TARGETED CLOSURE**

```
ARCHITECTURE CHECKPOINT B: CONDITIONAL PASS
NO MAJOR RESTRUCTURING REQUIRED
PHASE 4 NOT YET AUTHORIZED — 6 BLOCKING CLOSURE ITEMS
```

The Vision 5D architecture is structurally coherent. Phases 0-3 form one recognizable SaaS product with clear domain boundaries, no material duplication, and a well-defined data model. Six targeted closure items must be resolved before Phase 4 begins. None requires architectural redesign.

---

## 2. REPOSITORY EVIDENCE SUMMARY

### File Inventory

| Layer | Count | Lines | Key Files |
|-------|-------|-------|-----------|
| Domain/DB | 2 | 302 | `domain/models.py` (14 tables), `domain/database.py` |
| Contracts (P1) | 1 | 665 | `contracts/models.py` (shared Pydantic types) |
| Security | 1 | 64 | `security/crypto.py` (AES-256-GCM, tenant-keyed) |
| API (P1) | 1 | 547 | `apps/api/main.py` (17 endpoints) |
| API (P2) | 1 | 123 | `apps/api/plan_routes.py` (3 endpoints) |
| API (P3) | 1 | 317 | `apps/api/geometry_routes.py` (15 endpoints) |
| Worker | 1 | 162 | `apps/worker/main.py` (17-state machine) |
| Frontend (P1) | 1 | 236 | `apps/web/index.html` (Phase 1 Console) |
| Frontend (P3) | 1 | 300 | `apps/web/geometry-editor.html` (Canvas) |
| Phase 2 Engine | 6 | 1,672 | `plan_understanding/` (full pipeline) |
| Phase 3 Engine | 10 | 2,866 | `geometry/` (full pipeline) |
| Tests | 2 | 838 | `test_phase2.py` (19), `test_phase3.py` (55) |
| Config | 2 | 21 | `docker-compose.yml`, `.env.example` |
| **TOTAL** | **36** | **7,870** | |

### Empty package directories (scaffolding only)

| Package | Status |
|---------|--------|
| `packages/artifacts/` | `__init__.py` only |
| `packages/jobs/` | `__init__.py` only |
| `packages/hermes_bridge/` | `__init__.py` only |
| `packages/observability/` | `__init__.py` only |
| `packages/providers/` | `__init__.py` only |
| `packages/validation/` | `__init__.py` only |
| `migrations/` | Empty (no Alembic) |
| `docs/` | Empty |
| `evidence/` | Empty |
| `infrastructure/` | Empty |
| `scripts/` | Empty |

---

## 3. CURRENT ARCHITECTURE

### Layer-by-layer with repository evidence

```
┌─────────────────────────────────────────────────────┐
│ BROWSER                                              │
│  apps/web/index.html        (Phase 1 Console)        │
│  apps/web/geometry-editor.html (Phase 3 Canvas)      │
│  STATUS: Two standalone pages, no shared nav          │
│  INTEGRATION: Both call localhost:8000 directly       │
└───────────────┬─────────────────────────────────────┘
                │ HTTP (no auth on canvas, JWT on console)
┌───────────────▼─────────────────────────────────────┐
│ AUTHENTICATED API LAYER                              │
│  apps/api/main.py              (17 P1 endpoints)     │
│  apps/api/plan_routes.py       (3 P2 endpoints)      │
│  apps/api/geometry_routes.py   (15 P3 endpoints)     │
│  STATUS: In-memory session store (SESSIONS dict)     │
│  AUTH: /api/v1/auth/login (demo OAuth)               │
│  TENANT: get_current_user() → (user_id, tenant_id)   │
│  ROUTERS: All 3 registered via app.include_router()  │
└───────────────┬─────────────────────────────────────┘
                │ SQLAlchemy Session
┌───────────────▼─────────────────────────────────────┐
│ DATABASE                                             │
│  packages/domain/models.py     (14 tables)            │
│  packages/domain/database.py   (SQLite/PostgreSQL)    │
│  vision5d.db                   (SQLite, test data)    │
│                                                        │
│  TABLES: tenants, users, workspaces,                  │
│    workspace_memberships, projects,                   │
│    project_memberships, provider_configs,             │
│    secret_refs, encrypted_credentials,                │
│    artifacts, jobs, job_attempts,                     │
│    checkpoints, progress_events,                      │
│    validation_decisions, audit_events,                │
│    upload_sessions                                    │
│                                                        │
│  STATUS: No migrations (Alembic not configured)       │
│  TENANT ISOLATION: tenant_id FK on all tables         │
│  RLS: PostgreSQL-only (SQLite trusts API layer)       │
└───────────────┬─────────────────────────────────────┘
                │ Poll-based
┌───────────────▼─────────────────────────────────────┐
│ BACKGROUND WORKER                                    │
│  apps/worker/main.py            (162 lines)           │
│  STATUS: Polls jobs table, 17-state machine           │
│  JOB TYPES: "asset-intake" (simulated),               │
│             "provider-test" (simulated)               │
│  CHECKPOINTS: Creates Checkpoint rows                 │
│  RESUME: Not implemented (checkpoints not consumed)   │
│  GAP: Phase 2/3 pipelines run SYNCHRONOUSLY           │
│        in API request thread, not through worker      │
└───────────────┬─────────────────────────────────────┘
                │ Direct import (synchronous)
┌───────────────▼─────────────────────────────────────┐
│ DOMAIN ENGINES                                       │
│                                                        │
│  Phase 2 — Plan Understanding                         │
│    plan_understanding/pipeline.py   (orchestrator)     │
│    plan_understanding/preprocessing.py                │
│    plan_understanding/ocr.py         (Tesseract)       │
│    plan_understanding/detection.py  (OpenCV heuristics)│
│    plan_understanding/understanding.py                │
│    plan_understanding/graph.py      (Canonical Graph)  │
│    plan_understanding/contracts.py  (Pydantic models)  │
│    TESTS: 19/19 pass                                  │
│                                                        │
│  Phase 3 — Geometry Engine                            │
│    geometry/pipeline.py    (15-stage orchestrator)     │
│    geometry/primitives.py  (coord, walls, junctions)   │
│    geometry/thickness.py   (thickness estimation)      │
│    geometry/rooms.py       (room polygons)             │
│    geometry/openings.py    (opening placement)         │
│    geometry/scale.py       (metric calibration)        │
│    geometry/constraints.py (constraints + solver)      │
│    geometry/topology.py    (topology graph)            │
│    geometry/repair.py      (repair + uncertainty)      │
│    geometry/validation.py  (validator + metrics)       │
│    geometry/model.py       (editable model + undo)     │
│    geometry/contracts.py   (70+ Pydantic models)       │
│    TESTS: 55/55 pass                                  │
└───────────────┬─────────────────────────────────────┘
                │ In-memory only
┌───────────────▼─────────────────────────────────────┐
│ PERSISTENCE STATUS                                   │
│  Phase 2 Graph:   NOT persisted (in-memory per call)  │
│  Phase 3 Model:   NOT persisted (in-memory dict)      │
│  Artifacts:       DB rows exist, storage is mock       │
│  Upload Sessions: DB rows, content mock                │
│  Jobs/Checkpoints: DB rows, resume not wired           │
└─────────────────────────────────────────────────────┘
```

---

## 4. CAPABILITY OWNERSHIP MATRIX

| Capability | Owner | Producer | Consumers | DB Table | API | Frontend | Duplication |
|-----------|-------|----------|-----------|----------|-----|----------|-------------|
| Authentication | Phase 1 | `main.py::auth_login` | All phases | `users` | `POST /api/v1/auth/login` | Phase 1 Console | None |
| Users | Phase 1 | `domain/models.py::User` | All | `users` | (via auth) | Phase 1 Console | None |
| Tenants | Phase 1 | `domain/models.py::Tenant` | All | `tenants` | (via auth) | - | None |
| Workspaces | Phase 1 | `main.py::workspace_create` | All | `workspaces` | `POST /api/v1/workspaces` | Phase 1 Console | None |
| Projects | Phase 1 | `main.py::project_create` | P2, P3 | `projects` | `POST .../projects` | Phase 1 Console | None |
| Uploads | Phase 1 | `main.py::upload_init` | P2, P3 | `upload_sessions` | `POST .../upload` | Phase 1 Console | None |
| Provider Credentials | Phase 1 | `main.py::api_key_submit` | P3+ | `secret_refs`, `encrypted_credentials` | `POST .../credentials` | Phase 1 Console | None |
| Jobs | Phase 1 | `worker/main.py` | P2, P3 | `jobs`, `job_attempts` | `POST .../jobs` | Phase 1 Console | None |
| Checkpoints | Phase 1 | `worker/main.py` | P2, P3 | `checkpoints` | (via worker) | - | None |
| Artifact Storage | Phase 1 | `domain/models.py::Artifact` | P2, P3 | `artifacts` | `POST .../register` | - | Mock only |
| OCR | Phase 2 | `plan_understanding/ocr.py` | P2, P3 | - | `POST .../understand` | - | None |
| Plan Understanding | Phase 2 | `plan_understanding/pipeline.py` | P3 | - | `POST .../understand` | - | None |
| Architectural Graph | Phase 2 | `plan_understanding/graph.py` | P3 | - | `GET .../graph` | - | **NOT PERSISTED** |
| Scale Evidence | Phase 2 | `plan_understanding/understanding.py` | P3 | - | (in graph) | - | None |
| Metric Calibration | Phase 3 | `geometry/scale.py` | P4 | - | (in geometry) | - | None |
| Wall Geometry | Phase 3 | `geometry/primitives.py` | P4 | - | `GET .../geometry/model` | Geometry Canvas | None |
| Wall Thickness | Phase 3 | `geometry/thickness.py` | P4 | - | (in model) | - | None |
| Room Polygons | Phase 3 | `geometry/rooms.py` | P4 | - | (in model) | - | None |
| Openings | Phase 3 | `geometry/openings.py` | P4 | - | (in model) | - | None |
| Topology | Phase 3 | `geometry/topology.py` | P4 | - | (in model) | - | None |
| Constraints | Phase 3 | `geometry/constraints.py` | P4 | - | (in model) | - | None |
| Repair | Phase 3 | `geometry/repair.py` | P4 | - | (in model) | - | None |
| Validation | Phase 3 | `geometry/validation.py` | P4 | `validation_decisions` | `GET .../geometry/validation` | - | None (P1 validations separate) |
| Ambiguities | Phase 3 | `geometry/repair.py` | P4 | - | `GET .../geometry/ambiguities` | - | None |
| Version History | Phase 1 (projects) + Phase 3 (model) | `projects.version`, `geometry/model.py` | All | `projects` | - | - | **No artifact version table** |
| Undo/Redo | Phase 3 | `geometry/model.py` | P4 | - | `POST .../undo`, `.../redo` | Geometry Canvas | None |
| Evidence | Phase 3 | `geometry/routes.py` | P4 | - | `GET .../geometry/evidence` | - | None |
| Dashboard | Phase 1 | `apps/web/index.html` | User | - | - | All API calls | **No navigation to P3** |
| Geometry Review | Phase 3 | `apps/web/geometry-editor.html` | User | - | - | Canvas only | **Disconnected from P1** |

---

## 5. DUPLICATION AND CONFLICT REGISTER

### 5.1 Harmless Overlap

| Finding | Detail | Recommendation |
|---------|--------|----------------|
| Point2D in P3 contracts vs Detection.bounding_box in P2 | Both have x/y coordinate concepts. P3 uses its own Point2D, P2 uses tuples/dicts. Intentional domain boundary. | Accept. P3 geometry needs its own coordinate type. |
| ScaleCalibration (P2) vs ScaleCalibrationResult (P3) | P2 has `ScaleCalibration` in plan_understanding/contracts.py. P3 has `ScaleCalibrationResult` in geometry/contracts.py. Different names, related concept. P3 wraps P2 scale. | Accept. P3 extends P2 scale with conflict tracking. |

### 5.2 Technical Debt (not blocking)

| Finding | Detail | Recommendation |
|---------|--------|----------------|
| ValidationDecision exists in both P1 (`domain/models.py`) and P3 (`geometry/contracts.py`) | P1 DB model has `validator_skill_id`, `target_skill_id`. P3 Pydantic model has `validator_id`, `object_ref`, `issue_code`. Different schemas. | P1 validator models job-gate decisions. P3 validator models geometry-quality decisions. Accept as different domains. Merge schemas in Phase 5. |
| In-memory session store in main.py | `SESSIONS: dict[str, dict]` — production needs JWT. | Defer to Phase 5. Not blocking P4 geometry. |
| Two separate frontend HTML files | `index.html` and `geometry-editor.html` are disconnected. No shared navigation. | Defer to Phase 5. P3 canvas is functional verification tool. |

### 5.3 Blocking Conflicts

**None found.** No competing authoritative implementations that could corrupt data, execution, or future development.

---

## 6. SAAS USER-JOURNEY READINESS MATRIX

| Step | Status | Evidence |
|------|--------|----------|
| User signs in | ✅ IMPLEMENTED | `POST /api/v1/auth/login` → session token, demo OAuth |
| Opens workspace | ✅ IMPLEMENTED | `POST /api/v1/workspaces` → workspace + membership |
| Creates/opens project | ✅ IMPLEMENTED | `POST .../workspaces/{id}/projects` → project row |
| Uploads plan | ✅ IMPLEMENTED | Upload init → chunk → register → verify → screen → identify |
| Starts plan understanding | ✅ IMPLEMENTED | `POST /api/v2/projects/{id}/understand` (synchronous) |
| Observes progress | ⚠️ PARTIAL | Phase 2 runs in API thread — no progress events for UI |
| Reviews understanding result | ✅ IMPLEMENTED | API returns graph, rooms, walls, scale summary |
| Starts geometry reconstruction | ✅ IMPLEMENTED | `POST /api/v3/projects/{id}/geometry/reconstruct` |
| Observes durable job progress | ❌ MISSING | Phase 3 runs synchronously in API, not through worker |
| Reviews geometry/ambiguities | ✅ IMPLEMENTED | `GET .../geometry/model`, `.../validation`, `.../ambiguities` |
| Applies/saves corrections | ⚠️ PARTIAL | Edits work via API, but model not persisted to DB |
| Reloads application | ❌ MISSING | In-memory model lost on restart |
| Sees persisted state/versions | ❌ MISSING | No DB-backed geometry model persistence |

**Overall SaaS readiness: 8/13 steps implemented, 5 partial/missing.**

---

## 7. DATABASE AND PERSISTENCE REVIEW

### Canonical chain status

```
Source File (upload_sessions row)           ✅ ROW EXISTS
        ↓
Understanding Graph                         ❌ NOT PERSISTED (in-memory)
        ↓
Geometry Model                              ❌ NOT PERSISTED (Python dict)
        ↓
Future 3D Model                             ⬚ Phase 4
```

### Table coverage assessment

| Entity | DB Table | Persistent | Notes |
|--------|----------|------------|-------|
| Users | `users` | ✅ | |
| Tenants | `tenants` | ✅ | |
| Workspaces | `workspaces` | ✅ | |
| Memberships | `workspace_memberships`, `project_memberships` | ✅ | |
| Projects | `projects` | ✅ | Has `version` counter |
| Uploads | `upload_sessions` | ✅ | Content hash tracked |
| Provider Credentials | `secret_refs`, `encrypted_credentials` | ✅ | AES-256-GCM, tenant-keyed |
| Jobs | `jobs` | ✅ | 17-state machine, idempotency key |
| Job Attempts | `job_attempts` | ✅ | |
| Checkpoints | `checkpoints` | ✅ | Binary state, hash-verified |
| Progress | `progress_events` | ✅ | |
| Artifacts | `artifacts` | ✅ | Has `parent_artifact_id` for lineage |
| Validation | `validation_decisions` | ✅ | |
| Audit | `audit_events` | ✅ | |
| **Phase 2 Graph** | **NONE** | ❌ | Needs `understanding_graphs` + `graph_nodes` + `graph_edges` tables |
| **Phase 3 Model** | **NONE** | ❌ | Needs `geometry_models` + `geometry_walls` + `geometry_rooms` + `geometry_openings` tables |
| **Edit History** | **NONE** | ❌ | Needs `geometry_edits` table |
| **Graph/Model Versions** | **NONE** | ❌ | Needs versioned foreign keys |

---

## 8. INTEROPERABILITY STATUS

### Format Ownership

| Format | Phase | Status |
|--------|-------|--------|
| PNG | Phase 2 | ✅ Tested (test_plan.png) |
| JPEG | Phase 2 | ⬚ Supported by preprocessing pipeline but not tested |
| PDF | Phase 2 | ⬚ Not yet implemented |
| TIFF | Phase 2 | ⬚ Not yet implemented |
| DXF | Phase 3 | ⬚ Planned for P3.1 |
| SVG | Phase 3 | ⬚ Planned for P3.1 |
| IFC | Phase 4 | ⬚ Future |
| GLB/glTF | Phase 4 | ⬚ Future |

### Interoperability Matrices

The following matrices from the Phase 0 specification are not yet implemented as runtime components:
- Master Format Matrix — not implemented
- Master Object Model — not implemented
- Master Translation Matrix — not implemented
- Master Capability Matrix — partially covered by skill catalog
- Master Validation Matrix — partially covered by Phase 3 validators
- Master Export Matrix — not implemented
- Adapter Registry — not implemented
- Schema Version Registry — not implemented

**Assessment:** These are Phase 4-5 concerns. Not blocking for Phase 3 closure.

---

## 9. PHASE 3 CLOSURE LIST

### Already resolved (confirmed by tests)

| Item | Evidence |
|------|----------|
| Wall reconstruction | 55 tests pass, pipeline runs 15/15 stages |
| Wall thickness estimation | Thickness engine with explicit/paired/pattern methods |
| Room polygon generation | Convex hull from wall centerlines |
| Opening placement | Host wall assignment with position-along-wall |
| Scale calibration | Auto + dimension-derived + manual override |
| Topology building | Adjacency, containment, connectivity edges |
| Constraint enforcement | Parallel, perpendicular, shared-endpoint, horizontal/vertical |
| Repair engine | Gap closing, fragment merging, detached opening reattachment |
| Validation | 15 validators across walls/rooms/openings/topology |
| Uncertainty handling | Classification with critical/major/minor |
| Editable model | Add/move/rename/thickness with undo/redo |
| 2D Canvas editor | Rendering with pan/zoom/drag |
| API endpoints | 15 endpoints registered and documented |

### Required closure (6 items — blockers for Phase 4)

| # | Item | Impact | Work |
|---|------|--------|------|
| C1 | **DB persistence for Phase 2 graphs** | Phase 4 cannot trace provenance without persisted graph | Add `understanding_graphs`, `graph_nodes`, `graph_edges` tables. Wire graph builder to persist. |
| C2 | **DB persistence for Phase 3 geometry models** | Phase 4 3D models need versioned geometry input | Add `geometry_models`, `geometry_floors`, `geometry_walls`, `geometry_rooms`, `geometry_openings` tables. Wire pipeline to persist. |
| C3 | **Worker executes Phase 2/3 pipelines** | Phase 4 3D generation will time out if run synchronously | Move pipeline execution from API thread to worker. API submits durable jobs. |
| C4 | **Checkpoint-based resume for pipelines** | Phase 4 long-running 3D jobs must survive worker restart | Wire pipeline stages to worker checkpoints. Load last checkpoint on resume. |
| C5 | **Coordinate system wiring (px→mm)** | Room areas/wall lengths in px² not m² | Apply scale calibration transform in room/wall measurement. Store world coordinates. |
| C6 | **Browser-to-worker progress visibility** | User cannot see Phase 3 job progress | SSE or polling endpoint for job progress events. Wire to frontend. |

### Non-blocking debt

| Item | Recommendation |
|------|----------------|
| Alembic migrations | Run `alembic init` + autogenerate. Defer to Phase 4 setup. |
| JWT auth (vs in-memory sessions) | Defer to Phase 5. Demo OAuth sufficient for Phase 4 dev. |
| Frontend navigation unification | Defer to Phase 5 Interactive Studio. |
| Object storage (S3) | Mock storage strings fine for Phase 4 dev. Real storage in Phase 5. |
| Format adapters (PDF, DXF, SVG) | P3 validated with PNG. Add adapters incrementally during Phase 4. |

---

## 10. PHASE 4 READINESS ASSESSMENT

### What Phase 4 needs from Phase 3

| Phase 4 Input | Status | Blocking? |
|---------------|--------|-----------|
| Wall body polygons with world coordinates | P3 produces wall body polygons in px | C5 blocks |
| Room polygons with metric area | P3 produces rooms in px | C5 blocks |
| Opening positions along walls | ✅ Available | No |
| Wall thickness in mm | ✅ Available | No |
| Scale calibration (px→mm) | ✅ Calibration computed | C5 must apply it |
| Topology graph | ✅ Available (in-memory) | C2 blocks persistence |
| Validation decisions | ✅ Available (in-memory) | C1/C2 block traceability |
| Geometry version history | ✅ Undo/redo works (in-memory) | C2 blocks durability |
| Persisted provenance chain | ❌ Graph→Geometry→3D not persisted | C1/C2 block |

### Verdict: Phase 4 can begin development in parallel with C1-C6 closure, but cannot be certified complete until the provenance chain is durable.

---

## 11. RISK REGISTER

| # | Risk | Evidence | Impact | Probability | Blocks P4? | Action |
|---|------|----------|--------|-------------|------------|--------|
| R1 | Phase 2/3 run synchronously in API → timeout on large plans | Pipeline runs <1s on 17KB test image but scales O(n²) | MEDIUM | HIGH | YES (C3) | Move to worker |
| R2 | In-memory models lost on restart | `_geometry_models` and `_geometry_jobs` are Python dicts | HIGH | CERTAIN | YES (C2) | Persist to DB |
| R3 | Graph provenance chain broken | No DB tables for Phase 2/3 outputs | HIGH | CERTAIN | YES (C1) | Add tables |
| R4 | SQLite in production with concurrent workers | `check_same_thread=False` is workaround, not solution | MEDIUM | MEDIUM | NO | PostgreSQL for Phase 5 production |
| R5 | Tenant isolation on SQLite is manual | API filters by tenant_id but SQLite has no RLS | LOW | LOW | NO | PostgreSQL RLS for Phase 5 |
| R6 | Encryption key in memory, no KMS | `SecretEncryption` generates key at startup | MEDIUM | LOW | NO | KMS integration Phase 5 |
| R7 | No load testing | All pipelines tested on 17KB single image | LOW | MEDIUM | NO | Performance testing in Phase 5 |
| R8 | Frontend disconnected — no unified UX | Two standalone HTML files, no shared auth state | LOW | MEDIUM | NO | Phase 5 Interactive Studio |

---

## 12. ORDERED CORRECTIVE ACTIONS

### Closure Mission: V5D-CLOSE-004

**Goal:** Resolve 6 blocking items before Phase 4 certification.

| Step | Item | Description |
|------|------|-------------|
| 1 | C1 | Add `understanding_graphs`, `graph_nodes`, `graph_edges` DB tables. Wire graph builder to persist on pipeline completion. |
| 2 | C2 | Add `geometry_models`, `geometry_floors`, `geometry_walls`, `geometry_rooms`, `geometry_openings` DB tables. Wire pipeline to persist. |
| 3 | C3 | Create `plan-understanding` and `geometry-reconstruction` job types in worker. Move pipeline execution from API to worker. |
| 4 | C4 | Instrument pipeline stages as checkpoint boundaries. Implement resume from last checkpoint on worker restart. |
| 5 | C5 | Apply `ScaleCalibrationResult` transform to convert all px coordinates to mm in the geometry model output. |
| 6 | C6 | Add `GET /api/v3/projects/{id}/geometry/job` SSE endpoint or polling with progress events from worker. |

---

## 13. FINAL DECISION

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ARCHITECTURE CHECKPOINT B: CONDITIONAL PASS                ║
║                                                              ║
║   DECISION: B — TARGETED CLOSURE                             ║
║                                                              ║
║   PHASE 0–3 ARCHITECTURE: COHERENT                           ║
║   NO BLOCKING DUPLICATION FOUND                              ║
║   NO MATERIAL ARCHITECTURAL CONFLICT                         ║
║   6 TARGETED CLOSURE ITEMS IDENTIFIED                        ║
║                                                              ║
║   PHASE 4: NOT YET AUTHORIZED                                ║
║   PHASE 4 DEV CAN BEGIN IN PARALLEL WITH CLOSURE             ║
║                                                              ║
║   NEXT: V5D-CLOSE-004 (estimated 1 session)                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```
