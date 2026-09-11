# Vision 5D — Process Repair 005 — Blocker Report

**Verdict:** VISION 5D PROCESS REPAIR 005 = NOT CERTIFIED (BLOCKED)

## Exact blocker

A real multi-room property exists, but its canonical 3D scene/GLB is corrupted,
and no valid 3D multi-room scene exists to render from. The only available
geometry is 2D; rebuilding 3D requires the geometry-reconstruction stage
(PR001), which PR005 explicitly forbids repeating.

## Evidence

### Real multi-room property EXISTS
- Source CAD: `output/RE-SingDetch-FH_AS/input/RE-SingDetch-FH_AS.dwg` (867,879 bytes, R2000, mm units).
- Geometry model `geometry/HermesGeometryModel.v5d.json`: **18 rooms, 1010 walls, 105 doors**, 2703 entities, 23 layers.
- Design layer (`.v5d` export v2.1): 30 furniture items with 3D positions/dims/colors,
  6 named rooms (Living, + 5 others), 11 material types, lighting rigs, style "Modern Luxury".
- Prior output: 12-shot storyboard (`cinematic/storyboard.json`), 12 camera paths
  (`camera_paths.json`), 12 QA frames (`qa_frames/s01..s12.png`), and a 91s MP4
  (`cinematic/RE-SingDetch-FH_AS.mp4`).

### Canonical 3D scene/GLB is CORRUPTED
- `exports/RE-SingDetch-FH_AS.glb` (13,160 bytes): JSON chunk (2,401 bytes) holds only
  the 17 mesh NAMES (4 wall, 4 floor, 4 ceiling, 2 door, 2 window, 1 roof).
  The second chunk is garbage — type `0x42000029`, declared length 3,892,314,112
  (3.9 GB). No accessors, no bufferViews, no BIN geometry.
- Blender import fails: "Bad GLB: file size doesn't match" → 0 mesh objects.
- All 4 copies are byte-identical (MD5 `e4ec277edfbd8f1f5b1296f9be9faf25`) — no valid backup.

### No other valid 3D multi-room scene exists
- Every other GLB in the repo is the single living room (14 nodes: floor + 4 walls +
  9 furniture) — the PR001–PR004 scene, explicitly forbidden as a fallback.
- `data/cad/1579f70691d15b41.glb`, `version1/2.glb` are byte-identical copies of the
  same corrupted multi-room GLB.
- `.exports/50eeb35a…`, `probe_scene.glb`, `render_test_001/test_scene.glb` are invalid.
- No OBJ/FBX/DAE/PLY/STL/3DS files exist anywhere in the repo.
- The prior "cinematic" QA frames are 2D floor-plan visualizations (top-down),
  not 3D architectural walkthrough renders.

## Why this blocks PR005

PR005's target chain starts at "CANONICAL VISION 5D SCENE/GLB". The multi-room
property's GLB is unreadable (no geometry). The available geometry is 2D wall
line segments; producing a renderable 3D scene means the 2D→3D extrusion step of
PR001, which the mission lists as out of scope ("Do NOT: repeat PR001"), and the
mission forbids manually fabricating a scene to pass the test.

Per GOAL STAGE 1 ("If the available real property does not meet this requirement:
STOP → report exact limitation"), this is a stop-and-report blocker.

## First remaining customer-value gap

No valid 3D multi-room scene exists to tour; the canonical multi-room GLB is
corrupted down to its mesh names only.

## Next single repair

Regenerate the multi-room 3D scene/GLB from `HermesGeometryModel.v5d.json`
(2D walls → extruded 3D walls + 30 furniture items) and validate the GLB —
a geometry-reconstruction repair that belongs outside PR005's scope.

---
NO VALID 3D MULTI-ROOM SCENE EXISTS TO RENDER FROM
THE CANONICAL MULTI-ROOM GLB IS CORRUPTED (NO GEOMETRY BIN)
NO SINGLE-ROOM FALLBACK WAS USED
NO SYNTHETIC SCENE WAS FABRICATED
NO PRODUCTION MERGE WAS PERFORMED
