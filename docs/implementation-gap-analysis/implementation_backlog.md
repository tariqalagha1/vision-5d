# Implementation Backlog
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

**Total Estimated Effort**: 11 days (full-time)
**Phases**: 7 (each independently mergeable)
**Risk**: LOW — each phase is reversible, old artifacts preserved

---

## PHASE 1: GLB Export Fix [P0 — 2 days]

### 1.1 Fix glb_export.py accessor population [HIGH RISK — foundation]
**Problem**: `_build_gltf_json()` returns `"accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}]`.  
**Fix**: After building accessors/bufferViews in `export_glb()`, merge them into the glTF JSON dict returned by `_build_gltf_json()`.  
**Files**: `packages/scene3d/glb_export.py` (~30 lines changed)  
**Test**: GLB opens in GLTFValidator, all accessors resolve, all meshes visible  
**Depends on**: Nothing  
**Mergeable**: Yes

### 1.2 Add GLB validation utility [MEDIUM]
**New**: `packages/scene3d/glb_validator.py` — validates GLB binary structure  
**Test**: Runs against known-good and known-bad GLBs  
**Depends on**: 1.1  
**Mergeable**: Yes

### 1.3 Regression test with sample data [LOW]
**Test**: Run fixed export with existing Scene3D object, compare to expected GLB  
**Depends on**: 1.1

---

## PHASE 2: SceneGraph Serialization [P0 — 2 days]

### 2.1 Define .v5d binary format [MEDIUM]
**New**: `docs/v5d-format-spec.md`  
**Content**: Header (magic, version, byteLength), JSON segment (semantic objects), BIN segment (mesh data), checksum  
**Depends on**: Nothing  
**Mergeable**: Yes

### 2.2 Implement v5d_format.py [MEDIUM]
**New**: `packages/scene3d/v5d_format.py`  
**Functions**: `serialize(scene_graph) → bytes`, `deserialize(bytes) → SceneGraph`  
**Test**: Round-trip: SceneGraph → .v5d → SceneGraph (identical)  
**Depends on**: 2.1  
**Mergeable**: Yes

### 2.3 Implement mesh_generator.py [MEDIUM]
**New**: `packages/scene3d/mesh_generator.py`  
**Functions**: WallSolid → MeshData, FloorSlab → MeshData, CeilingSurface → MeshData, DoorElement → MeshData, WindowElement → MeshData, FurnitureInstance → MeshData  
**Test**: All generated meshes have vertices > 0, indices > 0, triangles > 0  

---

## PHASE 3: Unified Pipeline [P0 — 2 days]

### 3.1 Create v5d_pipeline.py [MEDIUM]
**New**: `scripts/v5d_pipeline.py`  
**Content**: 10-stage pipeline (DXF parse through GLB export), per-stage approval gates, SHA-256 chain  
**Depends on**: Phase 1, Phase 2  
**Mergeable**: Yes

### 3.2 Add approval gate system [LOW]
**New**: Stage approval JSON files at each stage  
**Test**: Verify gate prevents progression on failure  

### 3.3 Add hash provenance chain [LOW]
**Feature**: Each stage records input SHA-256 → output SHA-256  
**Test**: Chain is unbroken from DXF to GLB  

### 3.4 End-to-end test [CRITICAL]
**Test**: Full pipeline run with step02 DXF (`storage/projects/step02-e135eab76a86/input/RE-SingDetch-FH_AS.dxf`)  
**Verify**: All 10 stages pass, GLB is valid, HTML loads GLB  

---

## PHASE 4: HTML Viewer Rewrite [P0 — 1 day]

### 4.1 Create GLTFLoader-based template [HIGH]
**Rewrite**: `apps/web/cinematic.html` → new template  
**Required**: Uses `THREE.GLTFLoader`, loads GLB from relative path, NO BoxGeometry, NO PlaneGeometry, NO procedural geometry  
**Depends on**: Phase 1 (needs valid GLB)  
**Mergeable**: Yes

### 4.2 Embed camera paths [LOW]
**Feature**: Camera paths from SceneGraph embedded in HTML as JS array  
**Test**: Play button cycles through camera views  

### 4.3 Test with pipeline GLB [CRITICAL]
**Test**: Load pipeline output GLB in viewer, verify node count matches, no errors  

---

## PHASE 5: Browser Video Recording [P0 — 2 days]

### 5.1 Playwright integration [MEDIUM — NEW DEPENDENCY]
**New**: `npm install playwright` or `pip install playwright`  
**Code**: `scripts/v5d_video_export.py` — launches headless browser, loads HTML viewer  
**Depends on**: Phase 4  
**Mergeable**: Yes

### 5.2 Frame capture pipeline [MEDIUM]
**Feature**: Capture canvas at 30fps during camera path playback  
**Test**: All frames non-blank  

### 5.3 FFmpeg encoding [LOW]
**Feature**: Pipe frames to FFmpeg for MP4 (H.264), WebM (VP9), GIF  
**Test**: Output plays in VLC, browser  

### 5.4 End-to-end video verification [CRITICAL]
**Test**: Extract 10 checkpoint frames, verify >5 unique perceptual hashes, verify content matches GLB render  

---

## PHASE 6: Validation Hardening [P1 — 1 day]

### 6.1 Rewrite production_validation.py [MEDIUM]
**Modify**: `scripts/production_validation.py` — add structural GLB checks, visual HTML checks, video frame checks  
**Depends on**: Phase 1  

### 6.2 Implement QA pipeline [MEDIUM]
**New**: `packages/validation/qa_pipeline.py` — read-only inspection at every stage  
**Test**: Rejects known-broken artifacts, approves known-good artifacts  

### 6.3 Add visual checks [LOW]
**Feature**: Headless browser screenshots compared to expected renders  

---

## PHASE 7: Cleanup [P1 — 1 day]

### 7.1 Delete duplicate scripts [LOW]
**Delete**: 7 pipeline/rendering scripts (~2,600 lines)  

### 7.2 Archive old artifacts [LOW]
**Archive**: `output/RE-SingDetch-FH_AS/`, `storage/projects/pipeline-9-stage/`, `storage/projects/job-6ab2448e5aa7/`  

### 7.3 Remove procedural HTML viewers [LOW]
**Archive**: 4 old HTML viewers  

### 7.4 Update dependencies and docs [LOW]
**Update**: `pyproject.toml`, `README.md`  

---

## Task Dependency Graph

```
Phase 1 (GLB fix) ──────────────────────────────────────┐
    │                                                    │
Phase 2 (SceneGraph) ────┐                               │
    │                    │                               │
Phase 3 (Pipeline) ──────┤── depends on 1,2              │
    │                    │                               │
Phase 4 (HTML) ──────────┤── depends on 1                │
    │                    │                               │
Phase 5 (Video) ─────────┤── depends on 3,4              │
    │                    │                               │
Phase 6 (Validation) ────┤── depends on 1                │
    │                    │                               │
Phase 7 (Cleanup) ───────┘── depends on 3                │
```

**Parallel work possible**: Phases 2, 4, and 6 can start after Phase 1 completes. Phase 3 depends on Phase 2. Phase 5 depends on Phases 3+4. Phase 7 waits for Phase 3.

---

## Effort Summary

| Phase | Tasks | Days | Risk | Can Parallel? |
|-------|-------|------|------|---------------|
| 1: GLB Fix | 3 | 2 | **HIGH** | No (foundation) |
| 2: SceneGraph | 3 | 2 | MEDIUM | After Phase 1 |
| 3: Pipeline | 4 | 2 | MEDIUM | After Phase 2 |
| 4: HTML | 3 | 1 | **HIGH** | After Phase 1 |
| 5: Video | 4 | 2 | MEDIUM | After Phase 3+4 |
| 6: Validation | 3 | 1 | MEDIUM | After Phase 1 |
| 7: Cleanup | 4 | 1 | LOW | After Phase 3 |
| **TOTAL** | **24** | **11** | | |

**With parallel work (2 developers)**: ~7 days
