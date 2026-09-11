# V5D-CASCADE-LEARNING-CHECK-001 — Final Report

**Date:** 2026-07-29
**Mission:** Determine whether Cascade reuses knowledge from previous Vision 5D projects

---

## Verdict

**CASCADE DOES NOT REUSE PREVIOUS PROJECT KNOWLEDGE**

---

## Methodology

A full-stack audit was performed across three layers:

1. **Database Schema** — All 20 tables and their foreign key relationships
2. **Pipeline Source Code** — Worker (998 lines), persistence layer (309 lines), and all 16 packages
3. **Filesystem Storage** — All storage directories, mock S3, evidence, outputs, caches, and hidden state

---

## Finding 1: Database Isolation (E01)

The database uses **triple-layer isolation**: `tenant_id` + `workspace_id` + `project_id`.

| Table Count | Cross-Project FKs | Shared References |
|---|---|---|
| 20 | 0 | 0 |

Every data table has a `project_id` foreign key. No table has a foreign key to another project's data. There are 24 projects in the database, each fully isolated.

---

## Finding 2: Pipeline Query Scoping (E02, E03)

Every query in the pipeline execution path filters by the current project:

**Worker (apps/worker/main.py):**
- Line 337: `project_id = job.project_id` — extracts from current job only
- Line 366: `persist_understanding_graph(db, job.tenant_id, project_id, ...)` — explicit scoping
- Line 378: `storage_key=f"v5d/{tenant_id}/projects/{project_id}/..."` — storage isolation
- Line 460: `db.query(GNDB).filter(GNDB.graph_id == graph_id)` — graph is project-scoped

**Persistence (packages/domain/persistence.py):**
- Lines 38-41: `filter(UnderstandingGraph.project_id == project_id, UnderstandingGraph.tenant_id == tenant_id)` — dual filter
- Lines 132-135: `filter(PersistedGeometry.project_id == project_id, PersistedGeometry.tenant_id == tenant_id)` — same pattern

**No code path reads another project's data.** There is no "load previous project results" function, no "find similar project" query, no cross-project JOIN.

---

## Finding 3: Storage Isolation (E04)

| Storage | Projects | Cross-Access |
|---|---|---|
| `storage/projects/` | 3 (UUID-named dirs) | None |
| `.storage/` (mock S3) | 27 files | None |
| `output/` | 1 project | None |
| `evidence/` | 16 mission folders | None |

Every file in `.storage/` encodes project UUID in its filename. No shared or global directories exist.

---

## Finding 4: No Vector Stores or Caches (E05, E06)

A full filesystem scan confirmed:
- **Zero** vector stores (no .npy, .pt, .faiss, .chroma, .pkl, .bin)
- **Zero** embedding databases
- **Zero** similarity indexes
- **Zero** memory files or session state
- Python `__pycache__/` directories contain only compiled bytecode (.pyc), not project data
- `.pytest_cache/` contains only test metadata

---

## What Cascade DOES Share (Excluded by Rules)

Per mission rules, these are NOT considered project learning:
- Shared Python source code (`packages/`, `apps/`)
- Fixed configuration (`.env`, `pyproject.toml`, `alembic.ini`)
- System prompts and model weights
- `test_plan.png` (shared test fixture)

---

## Why No Learning Is Possible

Cascade has **no mechanism** to learn from previous projects because:

1. Every database table is project-scoped with zero cross-project foreign keys
2. Every pipeline query filters by `project_id` + `tenant_id`
3. Storage is namespaced by project UUID at the filesystem level
4. No vector stores, embedding databases, or similarity indexes exist
5. No memory files, session state, or cross-project state mechanisms exist

Each project is processed as a **completely independent pipeline run** using only shared source code and configuration. Cascade starts from scratch for every new project.

---

## Evidence Files

| File | Description |
|---|---|
| `storage_inventory.json` | Complete storage location audit |
| `new_run_trace.json` | Pipeline code path audit with query analysis |
| `previous_project_reads.json` | Cross-project read detection results |
| `learning_evidence.json` | Structured evidence with confidence ratings |
| `final_report.md` | This report |

---

## Final Verdict

**CASCADE DOES NOT REUSE PREVIOUS PROJECT KNOWLEDGE**

**CASCADE LEARNING CHECK COMPLETE**

**NO PIPELINE CHANGES WERE MADE**
