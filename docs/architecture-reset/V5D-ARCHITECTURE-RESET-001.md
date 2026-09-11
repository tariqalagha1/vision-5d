# Vision 5D Production Architecture Reset
## V5D-ARCHITECTURE-RESET-001

**Mission**: Establish a single authoritative scene pipeline where every downstream artifact derives from exactly ONE scene.

**Date**: 2026-07-26  
**Status**: ARCHITECTURE RESET COMPLETE — WAITING FOR APPROVAL — IMPLEMENTATION NOT STARTED

---

## 1. CURRENT ARCHITECTURE

```
                        ┌─────────────────┐
                        │   DWG (source)   │
                        │ RE-SingDetch-FH  │
                        │   867,879 bytes  │
                        └────────┬────────┘
                                 │ LibreDWG 0.13.3
                                 ▼
                        ┌─────────────────┐
                        │  DXF (converted) │
                        │ 2,484,964 bytes  │
                        └────────┬────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  DXF Parser      │  │  pipeline_9stage │  │  cad_to_5d       │
│  + Geometry Pipe │  │  (one-shot)      │  │  _pipeline.py     │
│                  │  │                  │  │  (separate)       │
│  Produces:       │  │  Produces:       │  │  Produces:        │
│  GeometryModel   │  │  floor_plan.png  │  │  Scene3D object   │
│  .v5d.json       │  │  BoxGeometry GLB │  │  (internal)       │
│  205 KB          │  │  2D video MP4    │  │                   │
└────────┬─────────┘  └──────────────────┘  └────────┬──────────┘
         │                                            │
         │                                            ▼
         │                                   ┌──────────────────┐
         │                                   │  GLB Export       │
         │                                   │  glb_export.py    │
         │                                   │                   │
         │                                   │  BUG: accessors[] │
         │                                   │  bufferViews[]    │
         │                                   │  are EMPTY in     │
         │                                   │  final GLB JSON   │
         │                                   │                   │
         │                                   │  Produces:        │
         │                                   │  BROKEN GLB       │
         │                                   │  13,160 bytes     │
         │                                   └──────────────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  HTML Viewer     │     │  Video Renderer  │     │  Certification   │
│  index.html      │     │  render_         │     │  Script           │
│                  │     │  cinematic_      │     │                   │
│  NEVER LOADS     │     │  video.py        │     │  Checks only:     │
│  THE GLB         │     │                   │     │  - file existence  │
│                  │     │  Uses Pillow      │     │  - non-zero size   │
│  Creates own:    │     │  perspective proj │     │  - ffprobe metadata│
│  10 box walls    │     │  Draws 2D rects   │     │  - string matching │
│  1 floor plane   │     │  from JSON spec   │     │                   │
│  30 box furniture│     │                   │     │  Does NOT verify:  │
│  (BoxGeometry)   │     │  Produces:        │     │  - GLB renderable  │
│                  │     │  2D diagram MP4   │     │  - HTML loads GLB  │
│  Unrelated to    │     │  349 KB           │     │  - 3D video content│
│  GLB or source   │     │                   │     │                   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### Component Inventory

| Component | File | Lines | Purpose | Connected? |
|-----------|------|-------|---------|------------|
| DXF Parser | `packages/cad_import/dxf_parser.py` | ~400 | Parse DXF entities | YES → geometry |
| Geometry Pipeline | `packages/geometry/pipeline.py` | 247 | Walls, doors, rooms, scale, topology | YES → reconstruction |
| 3D Reconstruction | `packages/scene3d/reconstruction.py` | 836 | GeometryModel → Scene3D | PARTIAL → GLB export |
| GLB Export | `packages/scene3d/glb_export.py` | 192 | Scene3D → GLB bytes | **BROKEN** — accessors never populated |
| HTML Viewer | `output/.../cinematic/index.html` | 31 | Display scene in browser | **DISCONNECTED** — never loads GLB |
| Cinematic Engine | `packages/cinematic/engine.py` | 572 | Camera paths, storyboard | **DISCONNECTED** — feeds JSON spec, not GLB |
| Video Renderer | `scripts/render_cinematic_video.py` | 421 | Pillow → MP4 frames | **DISCONNECTED** — uses Pillow 2D, not 3D |
| 9-Stage Pipeline | `scripts/pipeline_9stage.py` | 471 | End-to-end one-shot | **SEPARATE** — bypasses all packages |
| CAD-to-5D | `scripts/cad_to_5d_pipeline.py` | 365 | End-to-end orchestration | **SEPARATE** — duplicates pipeline_9stage |
| Validation Scripts | `scripts/production_validation.py` | ~200 | Surface-level checks | **TOO SHALLOW** — no visual/structural checks |
| Studio | `packages/studio/` | ~5 files | GLB inspector, storage, export | PARTIAL — inspector works, export disconnected |

---

## 2. ROOT CAUSE ANALYSIS

### 2.1 Primary Root Cause: Multiple Independent Artifact Pipelines

The system has at least **four independent renderers** that all create their own version of the scene:

```
Renderer A: GLB Export (glb_export.py)
  → Produces structurally broken GLB (accessors never populated)
  → Source: Scene3D internal object

Renderer B: HTML Viewer (index.html)
  → Never loads the GLB
  → Creates procedural BoxGeometry walls (10 in a circle)
  → Creates procedural BoxGeometry furniture (30 items)
  → Source: embedded F[] JavaScript array

Renderer C: Video Renderer (render_cinematic_video.py)
  → Uses Pillow (2D drawing library), not a 3D renderer
  → Reads a JSON spec file, not the GLB
  → Uses custom world_to_screen() perspective math
  → Draws flat colored rectangles for furniture
  → Source: luxury_cinematic.json spec

Renderer D: 9-Stage Pipeline (pipeline_9stage.py)
  → Another independent pipeline
  → Produces its own floor_plan.png via Pillow
  → Creates its own architecture.glb
  → Complete separate artifact chain
```

### 2.2 Specific Failure Points

| Failure | Component | Cause | Effect |
|---------|-----------|-------|--------|
| **F1: Empty accessors** | `glb_export.py:139` | `_build_gltf_json()` returns `"accessors": []` — accessors/bufferViews are built in `export_glb()` local variables but never merged into the JSON | GLB structurally invalid, no loader can render it |
| **F2: HTML independence** | `index.html:19-24` | Creates procedural BoxGeometry. No GLBLoader import. No URL reference to GLB. | HTML scene shares zero geometry with GLB |
| **F3: 2D video renderer** | `render_cinematic_video.py:77` | Uses `world_to_screen()` perspective math + Pillow `ImageDraw` to draw 2D rectangles | Produces 2D schematic, not 3D rendered walkthrough |
| **F4: JSON as scene DB** | `HermesGeometryModel.v5d.json` | 205 KB JSON with 1,010 walls, 105 doors, 18 rooms — used as de facto scene storage but never converted to any renderable output | 1,010 walls exist as JSON but not in GLB, HTML, or video |
| **F5: Duplicate pipelines** | `pipeline_9stage.py`, `cad_to_5d_pipeline.py`, `new_job_9stage.py` | Three scripts each independently reimplement the full pipeline with different outputs | No single source of truth, inconsistent artifacts |
| **F6: Shallow validation** | `production_validation.py` | Checks file existence, non-zero size, ffprobe metadata, string matching. Never opens GLB in a viewer. | Certifies broken artifacts as "passed" |
| **F7: Dead-end geometry** | `GeometryPipeline → HermesGeometryModel.v5d.json` | The geometry model is written to JSON but reconstruction engine may not consume it properly, and GLB export definitely doesn't receive correct MeshData | 1,010 walls in model → 4 wall_solid meshes in GLB with zero data |

### 2.3 Failure Propagation Map

```
Source DWG (correct)
  ↓
DXF conversion (correct, LibreDWG)
  ↓
DXF Parser (correct, extracts entities)
  ↓
Geometry Model (correct, 1,010 walls, 105 doors, 18 rooms in JSON)
  ↓
  ├─→ GLB Export ──→ BROKEN GLB (F1: empty accessors)
  │      ↓
  │   HTML Viewer ──→ DISCONNECTED (F2: never loads GLB)
  │
  ├─→ Video Renderer ──→ DISCONNECTED (F3: 2D Pillow, not 3D)
  │
  ├─→ 9-Stage Pipeline ──→ SEPARATE ARTIFACTS (F5: duplicate pipeline)
  │
  └─→ Validation ──→ FALSE POSITIVE (F6: surface checks only)
```

---

## 3. NEW ARCHITECTURE: SINGLE AUTHORITATIVE SCENE

### 3.1 Design Principle

> Every downstream artifact SHALL consume ONLY the previous approved artifact.
> No artifact may recreate geometry.
> The authoritative scene IS the scene — there is no other.

### 3.2 Architecture Diagram

```
                              ┌──────────────────────┐
                              │  STAGE 0: INGESTION   │
                              │                      │
                              │  DWG (source)         │
                              │  → LibreDWG 0.13.3    │
                              │  → DXF (converted)    │
                              │                      │
                              │  Verify: SHA-256      │
                              │  Approved by: Step-01 │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  STAGE 1: CAD PARSE   │
                              │                      │
                              │  DXF Parser           │
                              │  → Entity extraction  │
                              │  → Layer mapping      │
                              │  → Block resolution   │
                              │                      │
                              │  Output: CADEntities  │
                              │  Verified: entity     │
                              │  counts, layer names  │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  STAGE 2: PLAN        │
                              │  UNDERSTANDING        │
                              │                      │
                              │  OCR + Detection      │
                              │  → Wall detection     │
                              │  → Room detection     │
                              │  → Opening detection  │
                              │  → Dimension reading  │
                              │  → Scale calibration  │
                              │                      │
                              │  Output: ArchGraph    │
                              │  Verified: wall count │
                              │  room count, scale    │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  STAGE 3: GEOMETRY    │
                              │  RECONSTRUCTION       │
                              │                      │
                              │  Wall body extrusion  │
                              │  → Thickness est.     │
                              │  → Room closure       │
                              │  → Opening placement  │
                              │  → Topology fix       │
                              │  → Constraint solve   │
                              │                      │
                              │  Output: GeometryModel│
                              │  Verified: valid walls│
                              │  closed rooms, no     │
                              │  overlaps             │
                              └──────────┬───────────┘
                                         │
                                         ▼
         ┌───────────────────────────────────────────────────────────────┐
         │                 STAGE 4: AUTHORITATIVE SCENE GRAPH             │
         │                                                               │
         │  ┌─────────────────────────────────────────────────────────┐  │
         │  │                   SceneGraph                             │  │
         │  │                                                         │  │
         │  │  Building3D                                             │  │
         │  │  ├── BuildingLevel 0 (Ground Floor)                     │  │
         │  │  │   ├── WallSolid[] (1,010 walls)                      │  │
         │  │  │   ├── FloorSlab[] (per room)                         │  │
         │  │  │   ├── CeilingSurface[] (per room)                    │  │
         │  │  │   ├── DoorElement[] (105 doors)                      │  │
         │  │  │   ├── WindowElement[] (from openings)                │  │
         │  │  │   ├── RoomVolume[] (18 rooms)                        │  │
         │  │  │   │   ├── wall_ids: UUID[]                           │  │
         │  │  │   │   ├── opening_ids: UUID[]                        │  │
         │  │  │   │   ├── floor_area_m2: float                       │  │
         │  │  │   │   ├── is_closed: bool                            │  │
         │  │  │   │   └── function: str                              │  │
         │  │  │   ├── FurnitureInstance[] (from AI design)           │  │
         │  │  │   │   ├── asset_id → FurnitureAsset                  │  │
         │  │  │   │   ├── room_id → RoomVolume                       │  │
         │  │  │   │   ├── position: Vec3, rotation: Vec3, scale: Vec3│  │
         │  │  │   │   └── color_override                             │  │
         │  │  │   ├── FurnitureAsset[] (library)                     │  │
         │  │  │   ├── Material[] (global + per-room)                 │  │
         │  │  │   │   ├── baseColor, roughness, metallic             │  │
         │  │  │   │   └── texture_ref, normal_map_ref                │  │
         │  │  │   ├── SceneLight[] (ambient + directional)           │  │
         │  │  │   └── Camera[] (default view)                        │  │
         │  │  │                                                     │  │
         │  │  │   MeshData[] (generated from all above)              │  │
         │  │  │   ├── vertices: float32[]                            │  │
         │  │  │   ├── indices: uint16/uint32[]                       │  │
         │  │  │   ├── normals: float32[]                             │  │
         │  │  │   ├── uvs: float32[]                                 │  │
         │  │  │   ├── material_id → Material                         │  │
         │  │  │   ├── object_id → source object UUID                 │  │
         │  │  │   └── bbox: BBox3                                    │  │
         │  │  │                                                     │  │
         │  │  │   SceneStatistics                                    │  │
         │  │  │   └── level_count, room_count, wall_count,           │  │
         │  │  │       mesh_count, vertex_count, triangle_count,      │  │
         │  │  │       total_floor_area_m2                            │  │
         │  │  └── BuildingLevel 1..N (upper floors if applicable)    │  │
         │  │                                                         │  │
         │  │   UNIFIED SERIALIZATION FORMAT (.v5d)                   │  │
         │  │   ========================================              │  │
         │  │   Canonical binary format containing:                   │  │
         │  │   - All semantic objects (JSON/MessagePack)             │  │
         │  │   - All mesh vertex/index/normal/uv data                │  │
         │  │   - All material definitions                            │  │
         │  │   - All camera/light definitions                        │  │
         │  │   - Checksum for integrity                              │  │
         │  │   - Version number                                      │  │
         │  └─────────────────────────────────────────────────────────┘  │
         │                                                               │
         │  THIS IS THE ONE AUTHORITATIVE SCENE.                         │
         │  EVERYTHING ELSE DERIVES FROM IT.                             │
         └───────────────────────┬───────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  STAGE 5:        │  │  STAGE 6:        │  │  STAGE 7:        │
│  GLB EXPORT       │  │  HTML VIEWER     │  │  VIDEO EXPORT    │
│                   │  │                  │  │                  │
│  Input: SceneGraph│  │  Input: GLB      │  │  Input: Browser  │
│  (.v5d)           │  │  (from Stage 5)  │  │  canvas render   │
│                   │  │                  │  │                  │
│  Export pipeline: │  │  Uses Three.js   │  │  Uses Playwright │
│  1. Iterate       │  │  GLTFLoader to   │  │  or Puppeteer to │
│     MeshData[]    │  │  load the GLB    │  │  record the      │
│  2. Build binary  │  │                  │  │  browser canvas  │
│     buffer        │  │  Camera control  │  │                  │
│  3. Build         │  │  from scene      │  │  Camera path     │
│     accessors[]   │  │  camera paths    │  │  from scene      │
│  4. Build         │  │                  │  │  camera paths    │
│     bufferViews[] │  │  Materials from  │  │                  │
│  5. Assemble GLB  │  │  glTF materials  │  │  Encodes H.264   │
│     binary        │  │                  │  │  MP4 + VP9 WebM  │
│                   │  │  NO procedural   │  │  + GIF preview   │
│  Output: valid    │  │  geometry        │  │                  │
│  glTF 2.0 GLB     │  │  creation        │  │  Output: MP4,    │
│  Verified: opens  │  │                  │  │  WebM, GIF       │
│  in any viewer,   │  │  Output: working │  │  Verified:       │
│  all accessors    │  │  HTML viewer     │  │  frame content   │
│  resolve, buffers │  │  Verified:       │  │  matches GLB     │
│  have data        │  │  scene == GLB    │  │  render          │
└──────────────────┘  └──────────────────┘  └──────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │  STAGE 8:            │
                      │  CUSTOMER DELIVERY   │
                      │                      │
                      │  Bundle:             │
                      │  • GLB file          │
                      │  • HTML viewer       │
                      │  • MP4 cinematic     │
                      │  • WebM cinematic    │
                      │  • GIF preview       │
                      │  • Thumbnail PNG     │
                      │  • Scene graph .v5d  │
                      │  • Artifact manifest │
                      │  • Validation report │
                      │                      │
                      │  All artifacts        │
                      │  share SHA-256       │
                      │  provenance chain    │
                      └──────────────────────┘
```

### 3.3 Data-Flow Diagram

```
DWG ──→ DXF ──→ CADEntities ──→ ArchGraph ──→ GeometryModel ──→ SCENE GRAPH (.v5d)
                                                                       │
                                                    ┌──────────────────┤
                                                    │                  │
                                                    ▼                  │
                                              GLB Export               │
                                              (accessors populated)    │
                                                    │                  │
                                                    ▼                  │
                                              GLB file (.glb)          │
                                              ┌─────────┐             │
                                              │ Verified │             │
                                              │ opens   │             │
                                              └────┬────┘             │
                                                   │                  │
                                    ┌──────────────┤                  │
                                    │              │                  │
                                    ▼              ▼                  │
                              HTML Viewer    Video Export              │
                              (loads GLB)    (records browser)        │
                                    │              │                  │
                                    ▼              ▼                  │
                              Customer         MP4 + WebM             │
                              HTML             + GIF                  │
```

**Key constraint**: The arrow direction is always ONE WAY. No stage recreates what came before. Each stage ADDS value (rendering, encoding, packaging) but NEVER rebuilds geometry.

### 3.4 Execution Sequence

```
Step 01: Source ingestion (DWG → DXF)           [LibreDWG]
Step 02A: DXF verification + workspace setup    [File ops]
Step 02B: DXF parse → CADEntities               [DXF Parser]
Step 03: Plan understanding → ArchGraph         [OCR + detection]
Step 04: Geometry reconstruction → GeometryModel [extrusion + topology]
Step 05: 3D scene assembly → SceneGraph         [reconstruction engine]
Step 06: AI design → furniture placement        [AI provider]
Step 07: Material assignment                    [material library]
Step 08: Lighting configuration                 [light placement]
Step 09: Mesh generation → MeshData[]           [triangulation]
Step 10: SceneGraph validation                  [internal QA]
Step 11: GLB export from SceneGraph             [binary writer]
Step 12: GLB validation (independent viewer)    [GLTFValidator]
Step 13: HTML viewer generation                 [template + GLBLoader]
Step 14: Browser validation                     [Playwright screenshot]
Step 15: Video recording (browser → MP4)        [Playwright + FFmpeg]
Step 16: Customer bundle assembly               [file packaging]
Step 17: Final QA (independent challenge)       [separate agent]
```

Each step has an approval gate. No step continues until the current step passes.

---

## 4. COMPONENT DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    VISION 5D RUNTIME                         │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Ingest   │  │ Parse    │  │ Geometry │  │ Scene       │  │
│  │ Engine   │  │ Engine   │  │ Engine   │  │ Engine      │  │
│  │          │  │          │  │          │  │             │  │
│  │ DWG→DXF  │  │ DXF→Ent  │  │ Extrude  │  │ Assemble    │  │
│  │ Verify   │  │ Classify │  │ Topology │  │ SceneGraph  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘  │
│       │              │              │               │         │
│       ▼              ▼              ▼               ▼         │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              SCENE GRAPH STORE (.v5d)                │    │
│  │  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐  │    │
│  │  │Semantic │ │MeshData[]│ │Material│ │Camera/Light│  │    │
│  │  │Objects  │ │          │ │Library │ │Definitions │  │    │
│  │  └─────────┘ └──────────┘ └────────┘ └───────────┘  │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                    │
│  ┌───────────────────────┼──────────────────────────────┐    │
│  │         EXPORT PIPELINE (read-only consumers)         │    │
│  │                          │                            │    │
│  │  ┌──────────┐  ┌────────┴─────┐  ┌────────────────┐  │    │
│  │  │GLB Export│  │HTML Generator│  │Video Recorder  │  │    │
│  │  │          │  │              │  │                │  │    │
│  │  │SceneGraph│  │Template +    │  │Playwright +    │  │    │
│  │  │→ GLB     │  │GLBLoader     │  │FFmpeg          │  │    │
│  │  └────┬─────┘  └──────┬───────┘  └───────┬────────┘  │    │
│  │       │               │                  │            │    │
│  └───────┼───────────────┼──────────────────┼────────────┘    │
│          │               │                  │                  │
│          ▼               ▼                  ▼                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │.glb file │  │index.html    │  │.mp4 .webm .gif   │        │
│  └──────────┘  └──────────────┘  └──────────────────┘        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              VALIDATION PIPELINE                      │    │
│  │                                                      │    │
│  │  Stage Validator → GLB Validator → HTML Validator    │    │
│  │  → Video Validator → Final QA (independent)          │    │
│  │                                                      │    │
│  │  Each validator:                                     │    │
│  │  • Verifies input hash                               │    │
│  │  • Inspects output structurally                      │    │
│  │  • Checks visual correctness                         │    │
│  │  • Records evidence                                  │    │
│  │  • Can REJECT but never REPAIR                       │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. ARTIFACT CONTRACTS

### 5.1 Stage Dependency Graph

```
STAGE 0: DWG source                 [no dependencies]
STAGE 1: DXF conversion             [depends on: STAGE 0]
STAGE 2: CADEntities                [depends on: STAGE 1]
STAGE 3: ArchGraph                  [depends on: STAGE 2]
STAGE 4: GeometryModel              [depends on: STAGE 3]
STAGE 5: SceneGraph (.v5d)          [depends on: STAGE 4 + AI design]
STAGE 6: GLB export                 [depends on: STAGE 5 only]
STAGE 7: HTML viewer                [depends on: STAGE 6 only]
STAGE 8: Video export               [depends on: STAGE 7 only]
STAGE 9: Customer bundle            [depends on: STAGE 6 + 7 + 8]
```

### 5.2 Artifact Specifications

| Artifact | Producer | Consumer | Format | Validation |
|----------|----------|----------|--------|------------|
| DWG source | External | Ingest Engine | .dwg (binary) | SHA-256, DWG version, LibreDWG parse |
| DXF converted | LibreDWG | DXF Parser | .dxf (text) | SHA-256, section count, entity count |
| CADEntities | DXF Parser | Plan Understanding | Python objects | Entity counts per type, layer names |
| ArchGraph | Plan Understanding | Geometry Engine | Pydantic model | Wall count, room count, scale confidence |
| GeometryModel | Geometry Engine | Scene Assembly | Pydantic model | Valid walls, closed rooms, no overlaps |
| **SceneGraph** | Scene Assembly | **ALL downstream** | .v5d (binary) | Structural integrity, mesh validity |
| GLB | GLB Export | HTML Viewer, QA | .glb (binary) | Opens in validator, accessors resolve, all meshes visible |
| HTML | HTML Generator | Browser, QA | .html | Loads GLB, no console errors, scene matches GLB |
| MP4 | Video Recorder | Customer | .mp4 (H.264) | Frame content matches browser render, camera motion visible |
| WebM | Video Recorder | Customer | .webm (VP9) | Same as MP4 validation |
| GIF | Video Recorder | Customer | .gif | Animated, non-blank frames |

### 5.3 Artifact Ownership

```
┌──────────────────────────────────────────────────────┐
│                 OWNERSHIP CHAIN                       │
│                                                      │
│  Ingest Engine        OWNS: DWG copy, DXF output     │
│  Parse Engine         OWNS: CADEntities              │
│  Plan Engine          OWNS: ArchGraph                │
│  Geometry Engine      OWNS: GeometryModel            │
│  Scene Engine         OWNS: SceneGraph (.v5d) ←──┐   │
│  GLB Exporter         OWNS: GLB file             │   │
│  HTML Generator       OWNS: HTML viewer          │   │
│  Video Recorder       OWNS: MP4, WebM, GIF       │   │
│                                                    │   │
│  NO COMPONENT MAY MODIFY ANOTHER'S ARTIFACT ──────┘   │
│  Components may only READ upstream artifacts.         │
└──────────────────────────────────────────────────────┘
```

---

## 6. VALIDATION STRATEGY

### 6.1 Stage-Level Validation

Every stage has a validation gate. The gate checks:

| Check | Description | Failing means |
|-------|-------------|---------------|
| Input verification | SHA-256 of input matches approved upstream | STOP — possible corruption |
| Output verification | Output file exists, non-zero, correct format | STOP — generation failed |
| Hash verification | Output SHA-256 computed and recorded | STOP — cannot provenance |
| Structural verification | Output parses correctly (GLB JSON valid, HTML loads, MP4 decodes) | STOP — broken artifact |
| Visual verification | Output renders: GLB shows geometry, HTML shows scene, MP4 shows frames | STOP — invisible artifact |
| Dependency verification | Output SHA-256 appears in next stage's input verification | WARN — chain break |

### 6.2 Independent QA Pipeline

```
                        ┌──────────────────┐
                        │   QA Pipeline     │
                        │  (read-only)      │
                        │                  │
                        │  For every stage:│
                        │  1. Read input   │
                        │  2. Read output  │
                        │  3. Compare      │
                        │  4. Validate     │
                        │  5. Report       │
                        │                  │
                        │  QA MAY:         │
                        │  • Inspect       │
                        │  • Compare       │
                        │  • Validate      │
                        │  • Reject        │
                        │  • Record        │
                        │                  │
                        │  QA MAY NOT:     │
                        │  • Generate      │
                        │  • Repair        │
                        │  • Modify        │
                        │  • Replace       │
                        └──────────────────┘
```

**QA checkpoints**:

1. **After DXF**: Verify source DWG SHA matches Step-01 manifest, DXF matches conversion report
2. **After GLB**: Open GLB in Three.js headless, count meshes, count vertices, verify all accessors resolve, screenshot from default camera
3. **After HTML**: Load HTML in headless browser, verify GLB URL loads successfully, count scene objects, compare to GLB mesh count, check no console errors
4. **After Video**: Extract frames at 0s, 25%, 50%, 75%, 100% of duration; verify non-blank frames; verify perceptual hash diversity indicates camera motion; verify frame content visually matches standalone GLB render

---

## 7. FORBIDDEN PATTERNS

The new architecture SHALL permanently prohibit:

| Forbidden Pattern | Detection Method | Consequence |
|-------------------|-----------------|-------------|
| `new BoxGeometry(...)` in HTML | Static analysis of .html | REJECT — use GLBLoader only |
| `new PlaneGeometry(...)` in HTML | Static analysis of .html | REJECT — use GLBLoader only |
| Procedural furniture creation in HTML | Static analysis of .html | REJECT — furniture must come from GLB |
| `PIL.ImageDraw` for video frames | Static analysis of video scripts | REJECT — use browser recording |
| `world_to_screen()` perspective math in video | Static analysis of video scripts | REJECT — use browser recording |
| `"accessors": []` in GLB JSON | Structural GLB validation | REJECT — must have populated accessors |
| `"bufferViews": []` in GLB JSON | Structural GLB validation | REJECT — must have populated bufferViews |
| `"byteLength": 0` for GLB buffer | Structural GLB validation | REJECT — must have actual byteLength |
| JSON as scene database for downstream | Data-flow analysis | REJECT — use .v5d SceneGraph |
| Multiple scripts implementing same pipeline | File inventory | REJECT — one pipeline only |
| Validation that checks only file existence | Code review of validators | REJECT — must do structural + visual checks |

---

## 8. UUID AND VERSIONING STRATEGY

### 8.1 UUID Strategy

Every object in the SceneGraph has a UUID:

```
SceneGraph       ← scene_id (UUID v4)
  Building3D     ← building_id
    BuildingLevel ← level_id
      WallSolid  ← solid_id, source_wall_id → GeometryWall.centerline_id
      DoorElement← door_id, source_opening_id → GeometryOpening.id
      RoomVolume ← volume_id, source_room_id → GeometryRoom.id
      Furniture   ← instance_id, asset_id → FurnitureAsset.asset_id
      Material    ← material_id
      MeshData    ← mesh_id, object_id → semantic source
```

### 8.2 Versioning

```
SceneGraph.version: int (monotonic, increments on any change)
SceneGraph.source_geometry_model_id: UUID (links to GeometryModel)
SceneGraph.source_geometry_version: int
SceneGraph.parent_scene_id: UUID (links to previous version if modified)
```

---

## 9. MIGRATION PLAN

### 9.1 What Can Be Saved

| Component | Status | Action |
|-----------|--------|--------|
| `packages/scene3d/contracts.py` | **Good** — complete, well-designed | KEEP, minor updates |
| `packages/geometry/pipeline.py` | **Good** — works correctly | KEEP as-is |
| `packages/geometry/primitives.py` | **Good** | KEEP |
| `packages/geometry/rooms.py` | **Good** | KEEP |
| `packages/cad_import/dxf_parser.py` | **Good** | KEEP |
| `packages/cad_import/fidelity_bridge.py` | **Good** | KEEP |
| `packages/scene3d/reconstruction.py` | **Good** — logic correct | KEEP, verify SceneGraph output |
| `packages/ai/` | **Good** | KEEP as-is |
| `packages/domain/` | **Good** | KEEP as-is |
| `packages/security/` | **Good** | KEEP |
| `packages/cinematic/engine.py` | **Good** — camera paths work | KEEP, but feed from SceneGraph not JSON |
| `tools/libredwg/` | **Good** | KEEP |

### 9.2 What Must Be Rewritten

| Component | Reason | Priority |
|-----------|--------|----------|
| `packages/scene3d/glb_export.py` | **Critical bug**: accessors/bufferViews never populated in JSON | **P0** |
| HTML viewer template | Must use GLTFLoader, not procedural geometry | **P0** |
| Video export | Must record browser, not draw 2D with Pillow | **P0** |
| Production validation | Must do structural + visual checks, not surface-only | **P0** |
| Pipeline orchestration | Unify into single pipeline, remove duplicates | **P1** |
| SceneGraph serialization | Implement .v5d binary format | **P1** |
| Independent QA pipeline | New: read-only inspection at every stage | **P1** |

### 9.3 What Must Be Deleted

| Component | Reason |
|-----------|--------|
| `scripts/pipeline_9stage.py` | Duplicate pipeline, bypasses packages |
| `scripts/new_job_9stage.py` | Duplicate pipeline |
| `scripts/render_cinematic_video.py` | Pillow 2D renderer — replaced by browser recording |
| `scripts/render_full_video.py` | Same problem |
| `output/RE-SingDetch-FH_AS/cinematic/index.html` | Procedural geometry viewer — replaced |
| `output/RE-SingDetch-FH_AS/exports/RE-SingDetch-FH_AS.glb` | Broken GLB — replaced |
| `output/RE-SingDetch-FH_AS/cinematic/RE-SingDetch-FH_AS.mp4` | 2D schematic video — replaced |
| All `storage/projects/pipeline-9-stage/` | Duplicate pipeline output |

### 9.4 Implementation Order

```
PHASE 1: Fix the GLB (1-2 days)
  1.1 Fix glb_export.py: merge accessors/bufferViews into glTF JSON
  1.2 Verify GLB opens in Three.js GLTFLoader headless
  1.3 Verify all meshes have vertices, all accessors resolve
  1.4 Regression test with sample DXF

PHASE 2: Fix the HTML Viewer (1 day)
  2.1 Rewrite viewer template to use GLTFLoader
  2.2 Remove all procedural geometry creation
  2.3 Add camera controls from SceneGraph camera paths
  2.4 Verify HTML loads GLB, scene objects match GLB node count

PHASE 3: Fix the Video Pipeline (2 days)
  3.1 Integrate Playwright for headless browser control
  3.2 Load HTML viewer → GLB → render frames → pipe to FFmpeg
  3.3 Verify video frames match standalone GLB render
  3.4 Implement camera path playback from SceneGraph

PHASE 4: Unify Pipeline (2 days)
  4.1 Create single pipeline.py consuming all stages in order
  4.2 Add approval gates at every stage
  4.3 Delete duplicate pipeline scripts
  4.4 Add hash provenance chain

PHASE 5: Validation Hardening (1 day)
  5.1 Rewrite validators for structural checks (GLB accessor resolution)
  5.2 Add visual checks (screenshot comparison)
  5.3 Add dependency chain verification

PHASE 6: SceneGraph Format (2 days)
  6.1 Define .v5d binary format spec
  6.2 Implement serializer/deserializer
  6.3 Migrate all consumers to read .v5d

PHASE 7: Independent QA Agent (1 day)
  7.1 Create QA pipeline that reads without writing
  7.2 Implement per-stage inspection
  7.3 Add rejection capability

Total estimated: 10-12 days for complete architecture reset
```

---

## 10. RISK ANALYSIS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Playwright not available on target system | Medium | High | Fallback to Puppeteer or headless Chrome with CDP |
| Browser rendering non-deterministic | Low | Medium | Fixed seed for materials, fixed camera paths, hash-based frame comparison with tolerance |
| SceneGraph format migration breaks existing storage | Low | High | Versioned format, backward-compatible reader for old versions |
| GLB size too large for customer delivery | Low | Low | Draco compression in GLB export (stage 6 extension) |
| Existing project data incompatible with new pipeline | Medium | Medium | Migration script to reprocess from DXF stage |
| Third-party GLTFLoader bugs | Low | Medium | Pin Three.js version, validate with reference GLBs |
| FFmpeg encoding failure on CI | Medium | Low | Pre-encode to PNG frames, then FFmpeg; fallback to software encoding |

---

## 11. CONCLUSION

The current architecture fails because it produces **four independent renderings** from **four separate pipelines** with **zero shared geometry**. The GLB has a critical code bug (empty accessors/bufferViews), the HTML viewer never loads the GLB, and the video renderer uses 2D drawing instead of 3D rendering.

The new architecture establishes ONE authoritative SceneGraph (.v5d) as the single source of truth. Every downstream artifact — GLB, HTML viewer, video — consumes ONLY the previous approved artifact. Geometry is created exactly once, in the SceneGraph assembly stage. Validation is structural and visual at every stage. Independent QA reads without writing.

**No BoxGeometry. No Pillow. No disconnected pipelines. No JSON-as-database. One scene. One pipeline. Verifiable at every step.**

---

## 12. ARCHITECTURE RESET COMPLETE

```
ARCHITECTURE RESET COMPLETE

WAITING FOR ARCHITECTURE APPROVAL

IMPLEMENTATION NOT STARTED
```
