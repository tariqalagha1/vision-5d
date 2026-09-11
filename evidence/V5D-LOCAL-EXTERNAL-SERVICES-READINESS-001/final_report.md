# V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001 — Final Report (Phase 2)

**Date:** 2026-08-01 10:40 UTC  
**Mission:** V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001  
**Verdict:** VISION 5D LOCAL EXTERNAL SERVICES PARTIALLY VERIFIED

---

## CONNECTED CHAIN (FULLY PROVEN)

```
test_data\1.webp
→ NVIDIA meta/llama-3.2-11b-vision-instruct (15.8s, real API)
→ structured understanding (floor_plan, Living Room, sofa/table/cabinet)
→ manual approval
→ Vision 5D project (20bf0835-adbc-4769-b3d1-7a94dd2ff107)
→ Pascal scene (v5d-auth-lr-final, v2, 26 nodes)
→ Pascal REST CRUD (verified)
→ Pascal MCP validate (valid=true)
→ furniture placement (sofa at [2.5, 0.5, 0])
→ immutable revision (v5d-auth-lr-final@v2)
→ authoritative GLB (4,644B, SHA-256: 05847523...)
→ GLB structural validation (10/10)
→ Blender 5.2.0 import (48 vertices, bounds [0,5]×[-6,0]×[-0.15,2.7])
→ diagnostic frame (1280×720, Cycles CPU, 16 samples)
→ 150 preview frames (1280×720, Cycles CPU, 4 samples, denoise, 27.5 min)
→ FFmpeg MP4 (H.264, yuv420p, 1280×720, 30fps, 5.000s)
→ PREVIEW_APPROVED
```

---

## VERIFIED CAPABILITIES

| # | Capability | Status | Detail |
|---|---|---|---|
| 1 | NVIDIA Vision | ✅ | meta/llama-3.2-11b-vision-instruct, 15.8s, floor_plan+L.Room+sofa |
| 2 | Pascal REPO | ✅ | Commit 42ac4be1, @pascal-app/core 0.9.2 |
| 3 | Pascal REST | ✅ | Next.js :3002, /api/health, /api/scenes CRUD |
| 4 | Pascal Editor | ✅ | Next.js :3002, editor UI |
| 5 | Pascal MCP | ✅ | 46 tools, validate_scene, smoke test passed |
| 6 | Pascal Security | ✅ | Origin validation, loopback bypass, auth |
| 7 | GLB Generation | ✅ | 4,644B, valid glTF 2.0 |
| 8 | GLB Validation | ✅ | Magic gLTF, v2, 264 vertices, finite bounds |
| 9 | Blender Import | ✅ | 5.2.0, 48 verts, .blend saved |
| 10 | Blender Render (Cycles) | ✅ | 150 frames, 1280×720, 4 samples, denoise |
| 11 | FFmpeg Encode | ✅ | 8.1.1, H.264, yuv420p, 30fps, 5.000s |
| 12 | Preview Content | ✅ | PREVIEW_APPROVED (all 150 frames valid) |
| 13 | Truthful Exit Codes | ✅ | Script-level exception boundary, non-zero on failure |
| 14 | Engine Resolution | ✅ | Runtime enum check, BLENDER_EEVEE_NEXT→BLENDER_EEVEE correction |
| 15 | Cycles Device Config | ✅ | CPU only (12th Gen i7-12700), GPU unavailable |
| 16 | Blender Attempt Recon | ✅ | 7 attempts reconciled, 3 false-zero-exits identified |

---

## RENDER ENGINE CLASSIFICATION

| Field | Value |
|---|---|
| Eevee requested engine | BLENDER_EEVEE / BLENDER_EEVEE_NEXT |
| Eevee runtime enum | BLENDER_EEVEE (NOT BLENDER_EEVEE_NEXT) |
| Eevee enum-correction result | BLENDER_EEVEE_NEXT resolved to BLENDER_EEVEE |
| Eevee headless recheck result | EXCEPTION_ACCESS_VIOLATION (Win32 Error #6, ChoosePixelFormat) |
| Eevee crash classification | ENGINE_RUNTIME_CRASH |
| Primary render mode | **CYCLES_CPU** |
| Cycles device | 12th Gen Intel Core i7-12700 (CPU) |
| GPU available | No (CUDA/OPTIX/HIP not found) |

---

## BLENDER ATTEMPTS RECONCILED

| Attempt | Engine | Exit | Classification |
|---|---|---|---|
| A | BLENDER_EEVEE | 11 (crash) | ENGINE_RUNTIME_CRASH |
| B | CYCLES (32 samples) | -15 (killed) | PROCESS_TERMINATED_EXTERNALLY |
| C | CYCLES | 0 (false) | INVALID_INPUT_ARTIFACT |
| D | N/A | 0 (false) | COMMAND_ARGUMENT_DEFECT |
| E | BLENDER_EEVEE_NEXT | 0 (false) | SCRIPT_CONFIGURATION_DEFECT |
| F | CYCLES | 0 | VALID_SUCCESS |
| G | CYCLES | 0 | VALID_PARTIAL_SUCCESS |

---

## PREVIEW RENDER

| Field | Value |
|---|---|
| Engine | CYCLES |
| Device | CPU |
| Samples | 4 |
| Denoise | True |
| Resolution | 1280×720 |
| Expected frames | 150 |
| Actual frames | 150 |
| Failed frames | 0 |
| Duration | 1654.0s (27.5 min) |
| Total size | 64,664,072 bytes |
| First frame | 393,945 bytes |
| Median frame | 402,514 bytes |

---

## PREVIEW MP4

| Field | Value |
|---|---|
| Path | `preview_150_living_room.mp4` |
| SHA-256 | 599c03aaf2b21cb675b466498cbcc7e7bf0da9a3d60fdc83a82a22a45b796583 |
| Codec | H.264 |
| Profile | High |
| Resolution | 1280×720 |
| Pixel format | yuv420p |
| FPS | 30.0 |
| Duration | 5.000s |
| Frames | 150 |
| Size | 170,746 bytes |
| Source GLB SHA-256 | 05847523f75fa3c56eb0919cdf0ec11fb4297d60804abba71f3a0b433520134e |

---

## REMAINING LIMITATIONS

| # | Issue | Impact |
|---|---|---|
| 1 | Test failure | 130/131 (credential lifecycle, pre-existing encryption config issue) |
| 2 | Backend render endpoint | Not wired to Blender subprocess |
| 3 | Frontend render workflow | Not tested |
| 4 | Full 1920×1080 render | Not completed (estimated ~2h on Cycles CPU) |
| 5 | Full video content validation | Not performed (requires full render) |
| 6 | Restart/interruption recovery | Not tested |
| 7 | EEVEE headless | CRASHED — unavailable on current runtime |

---

## FINAL VERDICT

**VISION 5D LOCAL EXTERNAL SERVICES PARTIALLY VERIFIED**

The authoritative chain from photo → NVIDIA → understanding → Pascal → correction → revision → GLB → Blender import → 150-frame Cycles CPU render → FFmpeg H.264 MP4 has been verified end-to-end. Pascal REST, editor, and MCP services are functional. Blender 5.2.0 imports and renders the authoritative GLB successfully with truthful exit codes.

Headless EEVEE is unavailable (runtime crash). The full 1920×1080 render and backend endpoint wiring remain pending. One pre-existing test failure (credential lifecycle, encryption config) persists.

---

**THE CONFIGURED VISION PROVIDER WAS USED**  
**PASCAL SERVICES WERE VALIDATED WITH A REAL VISION 5D SCENE**  
**BLENDER WAS ACTUALLY INSTALLED AND EXECUTED**  
**THE AUTHORITATIVE VISION 5D GLB WAS IMPORTED**  
**THE FINAL MP4 WAS ENCODED FROM REAL BLENDER-RENDERED PNG FRAMES**  
**NO PRODUCTION MERGE WAS PERFORMED**

---

VISION 5D LOCAL EXTERNAL SERVICES READINESS COMPLETE
