# Component Status Matrix
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

| # | Component | Current | Target | Reuse% | Rewrite% | Delete% | Risk | Effort |
|---|-----------|---------|--------|--------|----------|---------|------|--------|
| 1 | `packages/geometry/` (13 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 2 | `packages/scene3d/contracts.py` | Working | KEEP | 100 | 0 | 0 | Low | — |
| 3 | `packages/scene3d/reconstruction.py` | Working | KEEP | 95 | 5 | 0 | Low | 2h |
| 4 | `packages/scene3d/glb_export.py` | **BROKEN** | **REWRITE** | 40 | 60 | 0 | **HIGH** | 2d |
| 5 | `packages/scene3d/persistence.py` | Working | KEEP | 100 | 0 | 0 | Low | — |
| 6 | `packages/cad_import/` (2 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 7 | `packages/plan_understanding/` (8 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 8 | `packages/ai/` (6 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 9 | `packages/contracts/models.py` | Working | KEEP | 100 | 0 | 0 | Low | — |
| 10 | `packages/domain/` (4 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 11 | `packages/security/` (3 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 12 | `packages/studio/` (6 files) | Working | MODIFY | 70 | 30 | 0 | Med | 1d |
| 13 | `packages/cinematic/` (3 files) | Working | MODIFY | 80 | 20 | 0 | Med | 1d |
| 14 | `packages/universal_ingestion/` (4 files) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 15 | `packages/observability/` (1 file) | Working | KEEP | 100 | 0 | 0 | Low | — |
| 16 | `packages/artifacts/` (1 file) | Empty | **BUILD** | 0 | 0 | 0 | Low | 4h |
| 17 | `packages/jobs/` (1 file) | Empty | **BUILD** | 0 | 0 | 0 | Low | 4h |
| 18 | `packages/validation/` (1 file) | Empty | **BUILD** | 0 | 0 | 0 | Med | 1d |
| 19 | `apps/api/` (7 files) | Working | KEEP | 95 | 5 | 0 | Low | 2h |
| 20 | `apps/worker/main.py` | Working | KEEP | 95 | 5 | 0 | Low | 2h |
| 21 | `apps/web/*.html` (4 viewers) | **DISCONNECTED** | **REWRITE** | 20 | 80 | 0 | **HIGH** | 1d |
| 22 | `scripts/step01_isolation.py` | Working | KEEP | 100 | 0 | 0 | Low | — |
| 23 | `scripts/cad_to_5d_pipeline.py` | Duplicate | **DELETE** | 0 | 0 | 100 | Low | — |
| 24 | `scripts/pipeline_9stage.py` | Duplicate | **DELETE** | 0 | 0 | 100 | Low | — |
| 25 | `scripts/new_job_9stage.py` | Duplicate | **DELETE** | 0 | 0 | 100 | Low | — |
| 26 | `scripts/v5d_21_production.py` | Duplicate | **DELETE** | 0 | 0 | 100 | Low | — |
| 27 | `scripts/studio_workflow.py` | Duplicate | **DELETE** | 0 | 0 | 100 | Low | — |
| 28 | `scripts/render_cinematic_video.py` | 2D broken | **DELETE** | 0 | 0 | 100 | Low | — |
| 29 | `scripts/render_full_video.py` | 2D broken | **DELETE** | 0 | 0 | 100 | Low | — |
| 30 | `scripts/production_validation.py` | Shallow | **REWRITE** | 20 | 80 | 0 | Med | 1d |
| 31 | `scripts/certify_p5.py` | Shallow | MODIFY | 30 | 70 | 0 | Med | 4h |
| 32 | `scripts/full_5d_validation.py` | Shallow | MODIFY | 30 | 70 | 0 | Med | 4h |
| 33 | `scripts/real_cinematic_integration.py` | 2D | MODIFY | 60 | 40 | 0 | Med | 4h |
| 34 | `scripts/delivery_challenge.py` | Working | KEEP | 100 | 0 | 0 | Low | — |
| 35 | `scripts/browser_certify.py` | Working | MODIFY | 70 | 30 | 0 | Low | 2h |
| 36 | `tests/` (3 files) | Sparse | EXTEND | 70 | 30 | 0 | Med | 2d |

### Summary

```
KEEP:      23 components  (~17,300 lines)
MODIFY:     6 components  (~800 lines changed)
REWRITE:    3 components  (~550 lines rewritten)
BUILD:      3 components  (~900 lines new)
DELETE:     7 components  (~2,600 lines removed)
EXTEND:     1 component   (~400 lines new tests)

NET: -200 lines (fewer lines, better architecture)
```
