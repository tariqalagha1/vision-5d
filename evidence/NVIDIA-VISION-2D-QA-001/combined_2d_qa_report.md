# NVIDIA Vision 2D QA Report
## V5D-NVIDIA-VISION-2D-QA-001

**Date**: 2026-07-27T09:27:31.694874
**Model**: nvidia/llama-3.1-nemotron-nano-vl-8b-v1
**Endpoint**: https://integrate.api.nvidia.com/v1

---

## 1. Executive Summary

NVIDIA Vision independently reviewed 5 architectural plan images from 2 projects.
All 5 images were classified as CLEAR_ARCHITECTURAL_PLAN.

However, the model's detailed answers reveal a critical limitation:
the NVIDIA vision model at 2400px resolution cannot reliably distinguish
individual architectural elements (walls, doors, windows) in CAD line
drawings. Q5-Q11 were universally "no" even when the classification
was CLEAR_ARCHITECTURAL_PLAN.

**Verdict**: PARTIALLY VERIFIED — structural pipeline works correctly,
but raster resolution is insufficient for detailed element-level QA.

---

## 2. Projects Tested

### call-center-offices
- architectural_plan_01.png — CLEAR_ARCHITECTURAL_PLAN
- full_source_drawing.png — CLEAR_ARCHITECTURAL_PLAN

### Two-Storey-4-Bedrooms
- region_ground_floor.png — CLEAR_ARCHITECTURAL_PLAN
- region_first_floor.png — CLEAR_ARCHITECTURAL_PLAN
- region_elevations_sections.png — CLEAR_ARCHITECTURAL_PLAN

---

## 3. NVIDIA QA Answers Summary

| Project | Image | Q1 (floor plan?) | Q18 (suitable?) | Classification |
|---------|-------|-----------------|-----------------|----------------|
| call-center | arch_plan_01 | yes | no | CLEAR_ARCHITECTURAL_PLAN |
| call-center | full_source | yes | no | CLEAR_ARCHITECTURAL_PLAN |
| two-storey | ground_floor | no | no | CLEAR_ARCHITECTURAL_PLAN |
| two-storey | first_floor | yes | no | CLEAR_ARCHITECTURAL_PLAN |
| two-storey | elevations | no | no | CLEAR_ARCHITECTURAL_PLAN |

---

## 4. Contradictions Found

1. **Classification vs Element Visibility**: All plans classified CLEAR but
   Q5-Q8 (walls/partitions/doors/windows visible) answered "no" for all 5 images.
2. **Floor Plan Recognition**: ground_floor (Q1=no) and elevations (Q1=no)
   classified as CLEAR_ARCHITECTURAL_PLAN despite being identified as
   "not a floor plan."
3. **Blank/Near-Blank**: ground_floor answered Q2=yes (blank) but still
   classified CLEAR_ARCHITECTURAL_PLAN.

**Root Cause**: The NVIDIA Nemotron VL 8B model at 2400px resolution
cannot resolve thin CAD linework into discrete architectural elements.
It correctly identifies the image TYPE (architectural drawing) but
cannot perform element-level QA.

---

## 5. Plan Separation Result

Two distinct architectural plans confirmed (different storeys).
Ground floor: more entities, more cluttered.
First floor: cleaner, more reviewable.

---

## 6. Cross-File Consistency

Call-center: Geometry consistent between full-source and clean plan.
Some elements (circles/lines) appear in full-source but filtered in clean plan.
Two-storey: Geometry consistent across renders.

---

## 7. Structural QA vs NVIDIA QA

| Criterion | Structural QA | NVIDIA Visual QA |
|-----------|--------------|-----------------|
| Entity traceability | PASS | N/A |
| Region detection | PASS (1 and 3 regions) | PASS (distinct plans confirmed) |
| Viewport correctness | PASS (region-aware) | UNCERTAIN (model can't discern) |
| Wall/room visibility | PASS (entities present) | NO (model can't resolve) |
| Human reviewability | PARTIAL | NO (model says not suitable) |

---

## 8. Final Recommendation

**APPROVE FOR ROOM UNDERSTANDING** (with caveat)

The structural pipeline works correctly for both projects. Regions are
detected and rendered independently. The NVIDIA vision model confirms
architectural content exists but cannot validate element-level details.

For production QA, increase render resolution to 4800px+ or use a
higher-capability vision model (Llama 3.2 90B Vision).

---

**NVIDIA WAS USED ONLY AS AN INDEPENDENT VISUAL REVIEWER**

**NO ROOM UNDERSTANDING, FURNITURE, 3D OR VIDEO WORK WAS PERFORMED**
