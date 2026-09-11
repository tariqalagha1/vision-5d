# Dependency Graph
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

### Linear Pipeline (ALLOWED dependencies)

```
STAGE 0: DWG Source
    │
    ▼
STAGE 1: DXF Conversion  ← depends on STAGE 0
    │
    ▼
STAGE 2: CAD Parse       ← depends on STAGE 1
    │
    ▼
STAGE 3: Plan Understanding ← depends on STAGE 2
    │
    ▼
STAGE 4: Geometry Reconst.  ← depends on STAGE 3
    │
    ▼
STAGE 5: Scene Assembly     ← depends on STAGE 4 + AI
    │
    ├──────────────────────────┐
    ▼                          ▼
STAGE 6: Mesh Generation    STAGE 9: SceneGraph Validation
    │                          │
    ▼                          │
STAGE 7: Material Assignment   │
    │                          │
    ▼                          │
STAGE 8: Lighting Setup        │
    │                          │
    └──────────┬───────────────┘
               ▼
STAGE 10: GLB Export        ← depends on STAGE 5-9
    │
    ▼
STAGE 11: GLB Validation    ← depends on STAGE 10
    │
    ▼
STAGE 12: HTML Viewer       ← depends on STAGE 10
    │
    ▼
STAGE 13: HTML Validation   ← depends on STAGE 12
    │
    ▼
STAGE 14: Video Recording   ← depends on STAGE 12
    │
    ▼
STAGE 15: Video Validation  ← depends on STAGE 14
    │
    ▼
STAGE 16: Bundle Assembly   ← depends on STAGE 10,12,14,15
```

### Package-Level Dependencies

```
universal_ingestion  ← (no internal deps)
cad_import           ← (no internal deps)
plan_understanding   ← cad_import
geometry             ← plan_understanding
ai                   ← (no internal deps)
scene3d              ← geometry, ai
studio               ← scene3d
cinematic            ← scene3d
contracts            ← (no internal deps — shared by all)
domain               ← (no internal deps — SQLAlchemy)
security             ← (no internal deps)
observability        ← (no internal deps)
```

### Forbidden Dependencies (STRICTLY ENFORCED)

```
✗ HTML → SceneGraph         (must load GLB, not raw scene)
✗ Video → SceneGraph        (must record browser, not parse scene)
✗ Video → DXF/CADEntities   (must not parse source files)
✗ GLB Export → HTML         (export must not know about viewer)
✗ Validation → (write)      (validation is READ-ONLY)
✗ Any stage → stage+2       (linear chain only)
✗ Downstream → Upstream     (data flows one direction)
```

### Hidden Dependencies (CURRENT — to be resolved)

```
pipeline_9stage.py → cv2 (OpenCV)      → DELETE (script removed)
render_cinematic_video.py → PIL        → DELETE (script removed)
HTML viewers → cdn.jsdelivr.net        → PIN VERSION in template
production_validation.py → subprocess ffprobe → ADD to deps
step01_isolation.py → tools/libredwg/dwg2dxf.exe → DOCUMENT in README
```

### Circular Dependencies

**NONE.** All package imports flow inward (toward contracts/domain) and outward (toward API/worker).
