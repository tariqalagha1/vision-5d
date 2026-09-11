# Stage Contracts
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

### Stage 0: Source Ingestion

```
Executor:       scripts/step01_isolation.py
Inputs:         .dwg file
Outputs:        .dxf in step01-{job_id}/converted/
Validation:     SHA-256 copy match, DXF section count, entity count
Failure:        STOP — bad source file
Rollback:       Delete workspace
Recovery:       Fix source file, restart
Retry:          NONE — manual fix required
```

### Stage 1: DXF Parse

```
Executor:       packages/cad_import/dxf_parser.py
Inputs:         DXF text from Stage 0
Outputs:        CADDrawing object
Validation:     Entity count > 0, all 7 DXF sections present
Failure:        STOP — unparseable DXF
Rollback:       N/A (in-memory)
Recovery:       Fix DXF, re-ingest
Retry:          NONE
```

### Stage 2: Plan Understanding

```
Executor:       packages/plan_understanding/pipeline.py
Inputs:         CADDrawing
Outputs:        ArchGraph (walls, rooms, openings, scale)
Validation:     Wall count > 0, room count > 0, scale confidence > 0.5
Failure:        STOP — unrecognizable plan
Rollback:       N/A (in-memory)
Recovery:       Manually annotate plan
Retry:          NONE
```

### Stage 3: Geometry Reconstruction

```
Executor:       packages/geometry/pipeline.py
Inputs:         ArchGraph
Outputs:        GeometryModel (walls w/ thickness, closed rooms, openings)
Validation:     All walls valid, all rooms closed, no overlaps
Failure:        STOP — geometry cannot be reconstructed
Rollback:       N/A (in-memory)
Recovery:       Manual topology fix
Retry:          NONE
```

### Stage 4: AI Design

```
Executor:       packages/ai/ (provider_client, analysis, proposal)
Inputs:         GeometryModel (room metadata)
Outputs:        Furniture plan, material palette, lighting plan
Validation:     Furniture count > 0, all rooms furnished, no collisions
Failure:        CONTINUE — AI is advisory, use defaults
Rollback:       Use default layout
Recovery:       Re-run AI with different prompt
Retry:          Up to 3 attempts
```

### Stage 5: Scene Assembly

```
Executor:       packages/scene3d/reconstruction.py
Inputs:         GeometryModel + AI design
Outputs:        SceneGraph (.v5d) — THE AUTHORITATIVE SCENE
Validation:     Wall count matches GeometryModel, room count matches, all UUIDs valid, material count > 0
Failure:        STOP — authoritative scene cannot be assembled
Rollback:       Delete .v5d
Recovery:       Fix reconstruction logic, re-assemble
Retry:          NONE
```

### Stage 6: Mesh Generation

```
Executor:       NEW packages/scene3d/mesh_generator.py
Inputs:         SceneGraph (.v5d)
Outputs:        Updated SceneGraph with MeshData[] populated
Validation:     Every mesh: vertices > 0, indices > 0, triangles > 0, bbox valid
Failure:        STOP — cannot generate meshes
Rollback:       Revert to pre-mesh SceneGraph
Recovery:       Fix triangulation logic
Retry:          NONE
```

### Stage 7: Material Assignment

```
Executor:       NEW material library
Inputs:         SceneGraph (.v5d), AI material palette
Outputs:        Updated SceneGraph with materials assigned per mesh
Validation:     Every mesh has material_id, PBR properties valid
Failure:        CONTINUE — use default gray material
Rollback:       Use defaults
Retry:          Up to 2 attempts
```

### Stage 8: Lighting Setup

```
Executor:       NEW light placer
Inputs:         SceneGraph (.v5d)
Outputs:        Updated SceneGraph with lights configured
Validation:     At least 1 ambient + 1 directional, no light inside walls
Failure:        CONTINUE — use defaults
Retry:          Up to 2 attempts
```

### Stage 9: SceneGraph Validation

```
Executor:       NEW packages/validation/scene_validator.py
Inputs:         SceneGraph (.v5d)
Outputs:        ValidationReport (blocking/review/advisory)
Validation:     Zero blocking issues
Failure:        STOP if blocking — fix before proceeding
                WARN if review — note in report
                OK if advisory — proceed
Stop conditions: Blocking: missing geometry, zero meshes, zero materials, zero lights
```

### Stage 10: GLB Export

```
Executor:       packages/scene3d/glb_export.py (FIXED)
Inputs:         SceneGraph (.v5d) ONLY
Outputs:        Valid .glb file
Validation:     All accessors resolve, all bufferViews populated, opens in GLTFValidator, meshes visible
Failure:        STOP — primary deliverable
Rollback:       Delete GLB, fix export logic
Recovery:       Fix glb_export.py
Retry:          NONE — fix code, not re-run
```

### Stage 11: GLB Validation (Independent QA)

```
Executor:       NEW packages/validation/glb_validator.py (READ-ONLY)
Inputs:         .glb file
Outputs:        QA report, screenshot
Validation:     Opens in headless Three.js, node count matches, mesh count matches
Failure:        STOP — evidence captured
NEVER:          Modifies GLB, regenerates GLB, patches GLB
```

### Stage 12: HTML Viewer

```
Executor:       NEW HTML template renderer
Inputs:         .glb file + camera paths from SceneGraph
Outputs:        index.html
Validation:     Loads GLB without errors, scene node count matches, NO procedural geometry
Failure:        STOP
Forbidden:      BoxGeometry, PlaneGeometry, procedural anything
```

### Stage 13: HTML Validation

```
Executor:       NEW packages/validation/html_validator.py (READ-ONLY)
Inputs:         index.html
Outputs:        Screenshot, console log, object count
Validation:     GLB URL resolves, scene renders, no missing textures
Failure:        STOP
```

### Stage 14: Video Recording

```
Executor:       NEW scripts/v5d_video_export.py
Inputs:         index.html
Outputs:        .mp4 (H.264), .webm (VP9), .gif, thumbnail.png
Validation:     All output files non-zero
Failure:        STOP
Uses:           Playwright (headless browser) + FFmpeg
```

### Stage 15: Video Validation

```
Executor:       NEW packages/validation/video_validator.py (READ-ONLY)
Inputs:         .mp4, .webm, .gif
Outputs:        Frame analysis, GLB match report
Validation:     10 checkpoint frames non-blank, > 5 unique perceptual hashes, content matches GLB render
Failure:        STOP — evidence captured at frames/
```

### Stage 16: Bundle Assembly

```
Executor:       NEW packages/artifacts/manifest.py
Inputs:         All validated artifacts from Stages 10-15
Outputs:        Delivery directory, artifact manifest, SHA-256 chain
Validation:     All files exist, all SHAs match, total size reasonable
Failure:        STOP — incomplete bundle
```

---

## Universal Rules

1. **All failures are STOP conditions unless marked CONTINUE.**
2. **No stage may modify an artifact from a previous stage.**
3. **Retry counts: NONE = manual investigation required. Numbered = automatic retry.**
4. **QA stages (11, 13, 15) are READ-ONLY. They NEVER produce artifacts.**
5. **The SceneGraph (.v5d) is the only artifact that accumulates changes across stages (5-9).**
