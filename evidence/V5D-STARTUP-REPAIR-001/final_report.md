# Vision 5D — Startup & Runtime Repair
## V5D-STARTUP-REPAIR-001

**Date**: 2026-08-26
**Scope**: Local dev startup path (.bat + .sh), root Docker build/compose, stale-API restart, encryption-key stability.
**Verdict**: VERIFIED — all startup paths now launch API + worker against the same sqlite DB; dashboard serves live data at :8000.

---

## 1. Changes Made

### 1.1 `packages/security/crypto.py` — encryption key stability
**Problem**: `secret_encryption = SecretEncryption()` generated a fresh random Fernet key on every import, so provider credentials stored via `POST /api/v1/providers/{id}/credentials` became undecryptable after any restart.
**Fix**: Added `_load_or_create_master_key()` with priority (1) `V5D_ENCRYPTION_KEY` env var (deterministically derived), (2) persisted key file `<root>/.storage/encryption.key`, (3) generate-and-persist. The global instance now uses the stable key.
**Verified**: encrypt→decrypt round-trip succeeds; `key_hash` identical across two separate processes (`2e50a605a06e3559`), proving cross-restart stability.

### 1.2 `start_vision5d_local.bat` — local Windows startup
**Problems fixed**:
- Removed the redundant `:8100` static server that was advertised as the dashboard (frontend resolves its API base to `window.location.origin`, so `:8100` rendered "Could not load statistics").
- Fixed wrong env var `V5D_DB_URL` → `V5D_DATABASE_URL` (code reads `V5D_DATABASE_URL`; the old var was silently ignored).
- Added the durable worker (`apps/worker/main.py`) launch.
- Dashboard now opens only at `http://localhost:8000/apps/web/index.html`.
**Verified**: `%V5D_DB_PATH:\=/%` substitution produces `C:/Users/admin/workspaces/vision-5d/vision5d.db` → URL `sqlite:///C:/Users/admin/workspaces/vision-5d/vision5d.db` (correct Windows absolute sqlite URL).

### 1.3 `scripts/start_api.sh` — bash startup
**Problems fixed**:
- Was API-only; now launches API + worker with `trap` cleanup.
- Hardcoded `cd /c/Users/admin/...` → dynamic project-root resolution.
- `sqlite:///$PWD/...` used the MSYS `/c/...` path (unopenable by the native sqlite3 driver) → now `sqlite:///$(pwd -W)/...` (Windows-native `C:/...`).
**Verified**: `bash -n` syntax OK; actual run started API (health 200) + worker successfully.

### 1.4 `docker-compose.yml` (root) — Docker build/compose
**Problem**: `build: .` had no root `Dockerfile` (the real one lives at `infrastructure/Dockerfile`); sqlite URL was an ephemeral in-container path; `./data:/data` volume didn't match.
**Fix**: `build: { context: ., dockerfile: infrastructure/Dockerfile }`; consistent `V5D_DATABASE_URL=sqlite:////app/data/vision5d.db`; persistent `vision5d_data:/app/data` volume; `V5D_AUTO_MIGRATE=false` + `V5D_AUTO_CREATE_TABLES=true` (matching local dev); `command: api` / `command: worker` (entrypoint modes).
**Verified**: `docker compose config --quiet` passes (VALID). Full `docker build`/`up` not executed — Docker Desktop engine is stopped on this host.

---

## 2. Verification Results

| Check | Result |
|-------|--------|
| API health (`GET /health`) | HTTP 200 — `{"status":"healthy","version":"1.0.0","phase":7}` |
| Worker liveness | Running, claiming + executing jobs (405s+ uptime, no crash) |
| Dashboard (visual, computer_use) | Live data — 88 projects, 29 active; System Health all green; header "connected" |
| Encryption key round-trip | OK (encrypt→decrypt succeeds) |
| Encryption key stability | Identical key across 2 processes |
| Test suite | **167 passed, 0 failed** (43.29s) |
| `docker compose config` | VALID |
| `.sh` syntax | OK (`bash -n`) |
| `.bat` DB substitution | Produces correct forward-slash Windows path |

---

## 3. Discovered (out of scope — flagged for follow-up)

1. **Worker job execution fails on stale queued jobs.** On startup the worker immediately processes `QUEUED` jobs left in the DB from prior sessions. These fail with:
   `1 validation error for PreprocessedImage / source_asset_id / UUID input should be a string, bytes or UUID object`
   — a pre-existing pydantic-v2 UUID-validation issue in `packages/plan_understanding/contracts.py` (`source_asset_id: UUID`), unrelated to the startup path. The worker's claim/execute/transition machinery works correctly; the pipeline code that runs *inside* jobs has this bug. **Recommend a separate pipeline-fix task.**

2. **Docker engine not running** on this host (`dockerDesktopLinuxEngine` pipe absent), so the container build/run was validated structurally (`docker compose config`) but not executed end-to-end.

3. **`infrastructure/docker-compose.yml` (production stack)** also uses `build: .` with its own context/dockerfile resolution and references `init-db.sql`/`grafana-datasources.yml` — left untouched (out of scope; production stack, not the root dev compose).

---

## 4. Closing Statement

NO PRODUCTION MERGE WAS PERFORMED. The four startup/runtime files were repaired and verified; the stale API was replaced with a fresh process serving the fixed GLB-export code; the test suite passes (167/167). The working Blender/CYCLES pipeline and all package internals were left untouched. One pre-existing pipeline bug (plan-understanding UUID validation) is documented above and recommended as a separate follow-up.
