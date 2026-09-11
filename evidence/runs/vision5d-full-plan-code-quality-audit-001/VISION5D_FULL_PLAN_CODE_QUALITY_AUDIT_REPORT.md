# VISION5D_FULL_PLAN_CODE_QUALITY_AUDIT_REPORT.md
## VISION5D-FULL-PLAN-CODE-QUALITY-AUDIT-001

Date: 2026-09-11
Authoritative plan: V5D-ARCHITECTURE-RESET-001 + V5D-IMPLEMENTATION-GAP-ANALYSIS-001 (stage_contracts, implementation_backlog)

---

## A. Executive Verdict

**VISION5D_PLAN_IMPLEMENTATION_CERTIFIED_WITH_RESTRICTIONS**

---

## B. Executive Summary

Vision 5D has progressed from the frozen "broken" baseline (POST-RESET-TRUTH-RECONCILIATION-001, Jul 27) to a substantially working platform. The single-authoritative-scene principle is implemented in spirit and the two hardest foundations — geometry reconstruction (1010 walls / 18 rooms / 105 doors) and GLB export (the historical F1 empty-accessors bug) — are DONE and the GLB fix is runtime-verified. The API (105 routes), durable worker, full DB schema, and frontend dashboard are all operational and integrated, with real data (106 projects, 500 jobs).

However, the plan is NOT fully realized. Three material restrictions block full certification:

1. **The HTML viewer still fabricates procedural geometry (BoxGeometry/PlaneGeometry) instead of loading the GLB** — F2 from the architecture reset, never resolved. Stage 12 explicitly forbids this.
2. **The full 1010-wall building has never been exported/rendered end-to-end** — every valid GLB and Blender render is a small test scene (144-160 vertices). The plan's core customer deliverable (real building tour) is unproven at scale.
3. **Secondary plan items are incomplete**: .v5d binary format (JSON used instead), independent validation/QA packages, artifact manifest/provenance, and Phase-7 cleanup of duplicate pipelines.

Deviations from the literal plan (Blender render instead of Playwright browser recording; JSON .v5d instead of binary) are documented, not repaired — the Blender path is verified working.

**Customer value: PARTIAL.** The platform produces genuine geometry and a valid GLB + Blender render pipeline, but a customer cannot yet receive a verified tour of their actual building.

---

## C. Authority Sources

1. docs/architecture-reset/V5D-ARCHITECTURE-RESET-001.md (PRIMARY)
2. docs/implementation-gap-analysis/implementation_gap_analysis.md (PRIMARY)
3. docs/implementation-gap-analysis/stage_contracts.md (PRIMARY)
4. docs/implementation-gap-analysis/implementation_backlog.md (PRIMARY)
5. evidence/POST-RESET-TRUTH-RECONCILIATION-001/reconciliation_report.md (evidence)
6. evidence/V5D-BLENDER-RUNTIME-VERIFICATION-001/final_report.md (evidence)

Full map with conflicts: evidence/runs/vision5d-full-plan-code-quality-audit-001/authority_map.md

---

## D. Complete Requirements Matrix

24 material requirements. Full traceability in evidence/runs/.../requirements_matrix.md.

| Status | Count | IDs |
|--------|-------|-----|
| IMPLEMENTED_AND_VERIFIED | 14 | A1 A2 B1 B2 C1 D3 D4 E1 G1 I1 I2 I3 I4 I5 |
| IMPLEMENTED_NOT_RUNTIME_VERIFIED | 2 | D2 E2 |
| PARTIALLY_IMPLEMENTED | 6 | D1 D5 F2 G2 H1 K1 |
| MISSING_IMPLEMENTATION | 2 | F1 J1 |
| (DEVIATION, verified) | 1 | G1 (Blender vs Playwright) |

---

## E. Architecture Comparison

PLANNED (single authoritative scene):
DWG → DXF → CADEntities → ArchGraph → GeometryModel → **SceneGraph (.v5d binary)** → GLB → HTML viewer (GLTFLoader) → Browser video → Bundle.

ACTUAL:
DWG → DXF → CADEntities → ArchGraph → GeometryModel → **SceneGraph (.v5d JSON v2.1)** → GLB (FIXED) → [HTML viewer still procedural] / [Blender offline render → MP4] → ad-hoc .exports.

Match: geometry chain (Stages 0-4) and GLB export now conform.
Divergence: (a) .v5d JSON not binary; (b) render = Blender not Playwright; (c) HTML viewer not connected to GLB; (d) bundle/manifest absent.

---

## F. Functional Flow Comparison

| Workflow | Planned | Actual | Gap | Final Status |
|----------|---------|--------|-----|--------------|
| CAD ingest | DWG→DXF→parse | Working | — | VERIFIED |
| Plan understanding | OCR/detection → graph | Working (720 nodes / 816 edges in DB) | — | VERIFIED |
| Geometry | walls/rooms/openings | Working (1010/18/105) | — | VERIFIED |
| Scene assembly | .v5d binary | JSON .v5d | binary format missing | PARTIAL |
| Mesh gen | separate module | inside reconstruction.py | not modularized; full-scale unverified | PARTIAL |
| GLB export | valid GLB | FIXED, valid GLB | full-building GLB unproduced | VERIFIED (unit) |
| HTML viewer | GLTFLoader | procedural geometry | **not done** | BLOCKED |
| Video | Playwright record | Blender render (verified) | deviation, no ADR | VERIFIED (test) |
| Bundle | manifest + SHA-256 | not built | manifest missing | PARTIAL |

---

## G. Frontend Audit

Working: dashboard renders and is fully wired (login→stats→projects→health→activity all return real data). 105-route API. Studio/AI-config/pipeline pages present.

Defect: the 3D viewers (cinematic.html, studio.html, generated index.html) build procedural BoxGeometry/PlaneGeometry scenes instead of loading the authoritative GLB. Only 3d-viewer.html uses GLTFLoader. This is the primary customer-facing gap.

Note (fixed this session, prior to audit): dashboard boot flicker — the app rendered unauthenticated ("Disconnected"/"Session expired") before auto-login, then re-rendered. Fixed by deferring Router.start() until auth resolves (apps/web/js/app.js) plus a sidebar "undefined" item fix (components/ui.js).

## H. Backend Audit

Working: FastAPI (105 routes v1-v6), durable job worker (500 jobs / 559 attempts / 228 checkpoints), geometry/scene3d/render/studio/ai routes all durable-job driven. geometry pipeline and scene3d reconstruction are complete and well-structured.

Gaps: no dedicated validation/QA package; no artifact manifest; jobs package empty (state machine lives in worker).

## I. Data Audit

36-table schema is complete and populated with real data (no fixtures in the live path). geometry_walls/rooms/openings, scene3d_meshes/objects/versions, understanding_graphs, checkpoints, durable_artifact_refs, validation_decisions all present.

Gap: geometry_walls holds 20 rows (test projects) — the 1010-wall reference building was never persisted through the DB pipeline (it exists only in the legacy .v5d JSON file).

## J. Integration Audit

CONNECTED + VERIFIED: frontend → API → worker → DB (authenticated flow). API → geometry/scene3d/render (durable jobs). Scene → GLB (unit). GLB → Blender → MP4 (test).

DISCONNECTED: GLB → HTML viewer. Bundle/manifest.

## K. Rendering / 3D / 5D Pipeline Audit

- 3D geometry: VERIFIED (1010 walls, 18 rooms, 105 doors, meshes with vertices/triangles/normals).
- GLB export: VERIFIED (valid glTF 2.0, accessors + auto-normals).
- Rendering: VERIFIED at test scale (Blender 5.2 EEVEE/CYCLES → FFmpeg H.264).
- 5D "time/cost" dimension: NOT in the approved plan (plan is a 3D scene + tour pipeline; "5D" is branding). No time/cost/schedule capabilities required by authority. NOT_APPLICABLE.
- Camera paths / storyboard: present (cinematic/engine.py, camera_paths.json, storyboard.json).
- Multi-shot tour: QA frames s01-s12 exist; photo_tour clips exist (Aug 13) but provenance not audited to be a genuine full-building render.

## L. Runtime Verification

Full log: evidence/runs/.../runtime_verification.md. Highlights:
- API healthy (phase 7), worker running, 105 routes.
- GLB export produces valid GLB (accessors 3, NORMAL==POSITION counts) — reproduced this session.
- pytest (Python 3.14): 170 passed, 0 failed.
- Authenticated data flow verified end-to-end.

## M. Missing Features / Data Found

| Requirement | Root cause | Severity | Repair | Evidence | Status |
|-------------|-----------|----------|--------|----------|--------|
| HTML viewer loads GLB (F1) | Phase 4 never completed | HIGH | Rewrite viewers to GLTFLoader; consume valid GLB | cinematic.html procedural | OPEN |
| Full-building GLB+render (D2) | full pipeline only run on toy scenes | HIGH | Run DXF→geometry→scene→GLB→Blender on RE-SingDetch-FH | no full-building GLB exists | OPEN |
| .v5d binary format (D1) | Phase 2 skipped | MEDIUM | Implement v5d_format.py (magic/JSON/BIN/checksum) | .v5d is JSON | OPEN |
| Validation/QA packages (D5,E2,F2,G2) | Phase 6 partial | MEDIUM | Build packages/validation (glb/html/video validators) | empty __init__ | OPEN |
| Artifact manifest (H1) | Phase 6 not done | MEDIUM | Build packages/artifacts/manifest.py + SHA chain | empty __init__ | OPEN |
| Duplicate pipelines cleanup (J1) | Phase 7 not done | MEDIUM | Delete 7 dup scripts + procedural viewers | still present | OPEN |

EXTERNAL_DATA_REQUIRED: none — the real DWG/DXF source is present (RE-SingDetch-FH_AS.dwg, converted.dxf). No external data blocks certification.

## N. Repairs Performed

None of the audit-identified material gaps were repaired in this session — they are OPEN and documented above. (The GLB export F1 bug was already fixed in code prior to this audit; it was runtime-verified here, not repaired here.)

Separate pre-audit fix (same session): dashboard boot flicker — apps/web/js/app.js (defer Router.start() until auth), apps/web/js/components/ui.js (skip section-only sidebar placeholders), index.html (cache-bust v=17/v=15).

## O. Regression Results

pytest (Python 3.14): 170 passed, 0 failed. No regressions. (GLB export, geometry, plan-understanding, scene3d tests all green.)

## P. Real Output Validation

- Genuine: geometry (.v5d: 1010 walls/18 rooms/105 doors), valid GLB (produced by current export_glb), Blender MP4 (30 real frames), photo_tour clips.
- FAKE_SUCCESS risk: 212-byte empty GLBs and 10KB invalid GLBs sit alongside valid GLBs in .exports/ and are only distinguishable by structure, not filename. Any validation that checks existence/non-zero-size would falsely certify them (this is exactly how the legacy 98.6% acceptance score was invalidated).

## Q. Customer / Business Value Assessment

PARTIAL. A customer can create a project, ingest CAD, get real geometry, and the platform can export a valid GLB and render a real 3D MP4 (verified at test scale). But the customer cannot yet receive a verified tour of their actual building, because (a) the full-building pipeline run is unproven and (b) the shipped HTML viewer shows a fabricated scene rather than the real one.

## R. Remaining Risks

BLOCKERS: none that prevent the platform from running — but full certification is blocked by H1+H2 (customer-facing deliverables unproven).
HIGH: F1 (procedural HTML viewer), D2 (full-building unverified).
MEDIUM: D1 (.v5d binary), D5/E2/F2/G2 (validation), H1 (manifest), J1 (cleanup), G1 deviation (no ADR).
LOW: stale broken GLB, stale README, empty placeholder packages, deprecation warnings.

## S. Plan Completion Estimate (evidence-based)

- Requirements implemented (any level): 22/24 (92%)
- Requirements runtime-verified: 14/24 (58%)
- Integrations verified: 5/7 connected (frontend→API→worker→DB ✓, scene→GLB ✓, GLB→Blender→MP4 ✓; GLB→HTML ✗, bundle ✗)
- Critical workflows verified: geometry+GLB export verified; full-building render + HTML viewer NOT verified
- Required data completeness: schema 100%; reference-building data persisted only in legacy JSON, not DB (partial)

## T. Certification Rationale

CERTIFIED_WITH_RESTRICTIONS (not CERTIFIED, not NOT_CERTIFIED):

- The architecture and the hardest foundations are genuinely implemented and working: geometry (1010 walls), GLB export (F1 fixed + runtime-verified), Blender render, full API/worker/DB/frontend integration, 170 passing tests.
- Full certification is withheld because two plan-critical customer-facing capabilities are not met: the HTML viewer still fabricates geometry instead of loading the GLB (Stage 12 explicitly forbids this), and the full real-building pipeline (mesh→GLB→render→tour) has never been executed — only toy scenes have.

The next material action to move toward CERTIFIED is: run the full pipeline on the reference building (RE-SingDetch-FH, 1010 walls) to produce a valid full-building GLB, then wire the HTML viewer to load it via GLTFLoader.

---

NO PRODUCTION MERGE WAS PERFORMED.
