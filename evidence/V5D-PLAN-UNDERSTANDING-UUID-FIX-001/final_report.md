# Vision 5D — Plan-Understanding UUID Bug Fix
## V5D-PLAN-UNDERSTANDING-UUID-FIX-001

**Date**: 2026-08-26
**Scope**: Fix the pydantic-v2 UUID validation failure that caused worker `plan-understanding` jobs to fail.
**Verdict**: VERIFIED — pipeline now runs end-to-end (4 rooms, 5 walls, graph complete).

---

## 1. Symptom

On worker startup, stale `QUEUED` jobs failed immediately with:
```
1 validation error for PreprocessedImage
source_asset_id
  UUID input should be a string, bytes or UUID object
  [type=uuid_type, input_value=UUID(as_uuid='00000000-...0001'), input_type=UUID]
```

## 2. Root Cause (verified by reproduction)

`packages/domain/models.py` imported SQLAlchemy's PostgreSQL type as `UUID`:
```python
from sqlalchemy.dialects.postgresql import UUID
```
`apps/worker/main.py` then did a **star import** after its stdlib import:
```python
from uuid import uuid4, UUID          # stdlib uuid.UUID
from packages.domain.models import *   # leaked SQLAlchemy UUID, SHADOWING stdlib
```
Because `models.py` had no `__all__`, the star import re-bound `UUID` to `sqlalchemy.sql.sqltypes.UUID`. So `UUID("0000...")` constructed a SQLAlchemy **type object** (repr `UUID(as_uuid='...')`), which pydantic's `UUID` field rejected.

**Reproduction confirmed**: `from uuid import UUID; from packages.domain.models import *` → `UUID is uuid.UUID` was `False`, and `PreprocessedImage(source_asset_id=UUID(...))` raised the exact error.

## 3. Fix

Renamed the SQLAlchemy type import to avoid the collision (root-cause fix — removes the leaked name, so star imports can no longer shadow stdlib `UUID`):
```python
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
```
and updated all **142** `Column(UUID(as_uuid=...))` → `Column(PG_UUID(as_uuid=...))`.

**Verified**:
- `UUID is uuid.UUID` → `True` after the star import.
- `PreprocessedImage(source_asset_id=uuid.UUID(...))` → accepted.
- Full `plan_pipeline.process()` on `test_plan.png` → `graph_built complete=True nodes=30 edges=34 rooms=4 walls=5`.
- No external importers of `UUID` from `domain.models` (checked across all `*.py`), so the rename is safe.

## 4. Regression Risk

The rename is purely cosmetic — `PG_UUID` is the identical SQLAlchemy `UUID` type, so the DB schema is unchanged. Full test suite re-run after the change: **167 passed, 0 failed**.

## 5. Regression Test (added)

Added `tests/test_domain_models_import.py` with 3 tests asserting:
1. `packages.domain.models` does not expose a `UUID` name.
2. `from packages.domain.models import *` preserves stdlib `uuid.UUID`.
3. The SQLAlchemy type is available as `PG_UUID`.

Full suite after the fix + regression test: **170 passed, 0 failed** (167 prior + 3 new).

## 6. Closing Statement

NO PRODUCTION MERGE WAS PERFORMED. The bug was a stdlib-name shadowing caused by a SQLAlchemy `UUID` import leaking through a star import; fixed at the source by aliasing the type, and locked in with a regression test. The plan-understanding pipeline (worker job path) now completes end-to-end.
