# Vision 5D — Process Repair 003 — Final Report

**Verdict:** VISION 5D PROCESS REPAIR 003 = COMPLETE WITH RESTRICTIONS

## What was produced

One playable multi-shot property-tour MP4 through the real Vision 5D render pipeline
(Blender 5.2, CYCLES CPU), reusing the verified PR002 scene.

| Field | Value |
|---|---|
| Final MP4 | `evidence/V5D-PROCESS-REPAIR-003/pr003_property_tour.mp4` |
| Codec | H.264 (h264), yuv420p |
| Resolution | 1280×720 |
| FPS | 24 |
| Duration | 15.0 s (360 frames) |
| Size | 2,113,696 bytes |
| Shots | 6 (72/60/72/72/60/84 frames) |
| Transitions | 5 crossfades (0.5 s each) |
| Source GLB | `evidence/V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001/fixed_api_glb.glb` (14 meshes) |

## Reference property

A single living room reconstructed by the full chain (photo → NVIDIA understanding →
geometry): floor slab 5×4 m, 4 walls (front wall has a high window gap 2.7–3.8 m),
open entrance side at y=-4, sofa (base + backrest + 2 armrests) against the open side,
table (top + 4 legs) in front of the sofa. **This is exactly one room** — no bedroom,
kitchen, or second space exists in the reference scene.

## Shot plan (6 shots, all collision-valid)

| Shot | Area | Type | Purpose |
|---|---|---|---|
| 01 | exterior_context | orbit | Establish room footprint from outside |
| 02 | entrance_approach | approach | Move toward open entrance at eye level |
| 03 | living_walkthrough | walkthrough | Walk right side, reveal sofa + table |
| 04 | seating_orbit | orbit | Orbit the seating group |
| 05 | furniture_detail | dolly | Dolly toward sofa (FAILED framing) |
| 06 | hero_reveal | reveal | Pull up/back to show whole room |

## AI vision review (13 frames sampled across the full video)

Positives (confirmed by vision, not logs):
- Floor, walls, sofa, table render with differentiated materials across all shots.
- No black frames, no wall penetration, no severe clipping, well-lit.
- Crossfades are clean blends, no corruption.
- Tour order (context → approach → enter → seating → furniture → hero) is coherent.

Material defects found:
1. **shot_05 (furniture detail)** — the dolly ends ~1.1 m from the 2 m-wide sofa; the
   sofa overflows the frame and reads as an abstract flat surface ("not clearly
   recognizable as a couch"). This is an extreme-proximity failure the collision-only
   validation did not catch.
2. **shot_03 (walkthrough)** — the final ~0.2 s is aimed at an empty wall/floor corner
   (camera walked past the furniture before the crossfade).

## Coverage

Single room: 6 functional zones, all meaningfully represented → 100% of the one room.
This is NOT a multi-room property-coverage claim; the reference scene has only one room.

## Automation truth

DEVELOPER-ASSISTED. The 6-shot camera plan (start/end/target/purpose) was hand-authored
in `scripts/pr003/pr003_tour2.py`; property understanding came from manual geometry
analysis (`glb_dump.py`); tour order was hard-coded. Vision 5D did not autonomously
identify spaces or generate cameras this run.

## Product level

LEVEL 3 — WORKING VIDEO PROTOTYPE. Real multi-shot video generation works, but
automation, multi-room coverage, and one shot's framing remain materially incomplete.

---
THE FINAL MP4 CONTAINS REAL RENDERED ARCHITECTURE ACROSS 6 DISTINCT VIEWPOINTS
A COHERENT CLIENT JOURNEY WAS PRODUCED WITH CROSSFADE TRANSITIONS
ONE SHOT (FURNITURE DETAIL) IS TOO CLOSE AND DISORIENTING
THE REFERENCE PROPERTY IS A SINGLE ROOM — MULTI-ROOM COVERAGE NOT DEMONSTRATED
CAMERA PLANNING AND TOUR ORDER WERE DEVELOPER-AUTHORED, NOT AUTOMATIC
NO PRODUCTION MERGE WAS PERFORMED
