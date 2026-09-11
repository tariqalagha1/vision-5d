# Migration Checklist
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

### Pre-Migration

- [ ] V5D-ARCHITECTURE-RESET-001 approved
- [ ] V5D-IMPLEMENTATION-GAP-ANALYSIS-001 reviewed
- [ ] All stakeholders aligned on "one scene" principle
- [ ] Test DXF available: `storage/projects/step02-e135eab76a86/input/RE-SingDetch-FH_AS.dxf`
- [ ] LibreDWG 0.13.3 confirmed working: `tools/libredwg/dwg2dxf.exe`
- [ ] Python 3.11+ with all deps from pyproject.toml
- [ ] FFmpeg available for video encoding
- [ ] Playwright installed for browser recording
- [ ] GLTFValidator available for GLB validation
- [ ] Backup of current `output/` and `storage/` to archive

### Phase 1: GLB Export Fix

- [ ] Fix `glb_export.py`: merge accessors into glTF JSON
- [ ] Fix `glb_export.py`: merge bufferViews into glTF JSON
- [ ] Fix `glb_export.py`: set buffer byteLength to actual size
- [ ] Test: GLB opens in GLTFValidator
- [ ] Test: All accessors resolve
- [ ] Test: Meshes visible in headless Three.js
- [ ] Test: Regression with existing Scene3D test data

### Phase 2: SceneGraph Serialization

- [ ] Define .v5d binary format spec
- [ ] Implement `v5d_format.py`: serialize
- [ ] Implement `v5d_format.py`: deserialize
- [ ] Implement version field
- [ ] Implement SHA-256 integrity check
- [ ] Test: round-trip serialize/deserialize
- [ ] Implement `mesh_generator.py`: walls → MeshData
- [ ] Implement `mesh_generator.py`: floors → MeshData
- [ ] Implement `mesh_generator.py`: ceilings → MeshData
- [ ] Implement `mesh_generator.py`: doors → MeshData
- [ ] Implement `mesh_generator.py`: windows → MeshData
- [ ] Implement `mesh_generator.py`: furniture → MeshData
- [ ] Test: all meshes have non-zero vertex/index counts

### Phase 3: Unified Pipeline

- [ ] Create `v5d_pipeline.py` with 10-stage execution
- [ ] Add Stage 0-9 as defined in stage_contracts.md
- [ ] Add approval gates at every stage
- [ ] Add SHA-256 provenance chain
- [ ] Add artifact manifest generation
- [ ] Test: full pipeline run with step02 DXF
- [ ] Test: all stage outputs validated
- [ ] Test: pipeline idempotent (same input → same output)

### Phase 4: HTML Viewer

- [ ] Create GLTFLoader-based HTML template
- [ ] Embed GLB path (relative)
- [ ] Embed camera paths from SceneGraph
- [ ] Add play/pause/next/prev controls
- [ ] Add room-name overlays from camera paths
- [ ] Test: loads GLB without console errors
- [ ] Test: scene node count matches GLB
- [ ] Test: NO BoxGeometry in output HTML
- [ ] Test: NO PlaneGeometry in output HTML
- [ ] Test: NO procedural furniture creation

### Phase 5: Browser Video Recording

- [ ] Implement Playwright integration
- [ ] Load HTML viewer in headless browser
- [ ] Play camera path sequence
- [ ] Capture canvas frames at 30fps
- [ ] Pipe frames to FFmpeg (H.264 MP4)
- [ ] Encode VP9 WebM from same frames
- [ ] Generate GIF preview (5fps, 15s)
- [ ] Generate thumbnail PNG (frame 0)
- [ ] Test: all output files non-zero
- [ ] Test: MP4 plays in VLC
- [ ] Test: WebM plays in browser
- [ ] Test: GIF animates

### Phase 6: Validation Hardening

- [ ] Rewrite `production_validation.py` for structural checks
- [ ] Add GLB accessor resolution check
- [ ] Add bufferView population check
- [ ] Add headless GLB render screenshot
- [ ] Add HTML GLB-load check
- [ ] Add video frame content check
- [ ] Implement QA pipeline (read-only)
- [ ] Test: known-bad GLB REJECTED
- [ ] Test: known-good GLB APPROVED

### Phase 7: Cleanup

- [ ] Delete: `cad_to_5d_pipeline.py`
- [ ] Delete: `pipeline_9stage.py`
- [ ] Delete: `new_job_9stage.py`
- [ ] Delete: `v5d_21_production.py`
- [ ] Delete: `studio_workflow.py`
- [ ] Delete: `render_cinematic_video.py`
- [ ] Delete: `render_full_video.py`
- [ ] Archive: `output/RE-SingDetch-FH_AS/`
- [ ] Archive: `storage/projects/pipeline-9-stage/`
- [ ] Archive: `storage/projects/job-6ab2448e5aa7/`
- [ ] Archive: `apps/web/3d-viewer.html`
- [ ] Archive: `apps/web/cinematic_luxury.html`
- [ ] Archive: `apps/web/cinematic_v2.html`
- [ ] Archive: `apps/web/geometry-editor.html`
- [ ] Update `pyproject.toml` dependencies
- [ ] Update `README.md` with new pipeline instructions
- [ ] Verify: no imports reference deleted files

### Post-Migration

- [ ] Full pipeline run produces valid artifacts
- [ ] Independent QA challenge passes
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Team notified of new pipeline
