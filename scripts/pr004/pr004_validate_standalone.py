"""PR004 — standalone validation evidence (no Blender needed).

Proves the ORIGINAL shot_05 (from PR003) fails the new generalized validator
and the REPLACEMENT shot_05 passes, using the actual furniture AABBs from the
reference GLB (fixed_api_glb.glb), converted to Blender world coordinates.
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera_validator import validate_path, MIN_DISTANCE, MAX_FILL, MIN_FILL

# Furniture AABBs in Blender world coords (from glb_dump of fixed_api_glb.glb,
# glTF Y-up -> Blender Z-up: Blender(x,y,z) = GLB(x,-z,y)).
FURNITURE = [
    ((1.5, -3.7, 0.1), (3.5, -2.8, 0.5)),    # sofa base
    ((1.5, -2.95, 0.5), (3.5, -2.8, 1.2)),   # sofa backrest
    ((1.5, -3.7, 0.5), (1.65, -2.8, 1.1)),   # armrest L
    ((3.35, -3.7, 0.5), (3.5, -2.8, 1.1)),   # armrest R
    ((1.9, -2.4, 0.7), (3.1, -1.6, 0.75)),   # table top
    ((1.95, -1.73, 0.1), (2.03, -1.65, 0.7)),  # table leg FL
    ((2.95, -1.73, 0.1), (3.03, -1.65, 0.7)),  # table leg FR
    ((1.95, -2.33, 0.1), (2.03, -2.25, 0.7)),  # table leg BL
    ((2.95, -2.33, 0.1), (3.03, -2.25, 0.7)),  # table leg BR
]

# Combined sofa+table arrangement (the intended framing target).
TARGET = ((1.5, -3.7, 0.1), (3.5, -1.6, 1.2))

# Default Blender camera (50mm, 36mm sensor, 16:9 render): hfov=39.6 deg.
HFOV_HALF = 19.8
VFOV_HALF = 11.45

ORIGINAL = {
    "id": "shot_05_original",
    "start": (2.5, -6.5, 1.4),
    "end": (2.5, -4.8, 1.3),
}
REPLACEMENT = {
    "id": "shot_05_replacement",
    "start": (2.5, -8.0, 1.6),
    "end": (2.5, -6.8, 1.5),
}

out = {"thresholds": {"min_distance_m": MIN_DISTANCE,
                      "max_fill": MAX_FILL, "min_fill": MIN_FILL},
       "hfov_half_deg": HFOV_HALF, "vfov_half_deg": VFOV_HALF}

for s in (ORIGINAL, REPLACEMENT):
    r = validate_path(s["start"], s["end"], FURNITURE, TARGET,
                      HFOV_HALF, VFOV_HALF)
    r["shot"] = s["id"]
    out[s["id"]] = r
    verdict = "PASS" if r["valid"] else "FAIL"
    print(f"{s['id']}: {verdict}  min_dist={r['min_distance_m']}m "
          f"fill_h={r['end_fill_h']} fill_v={r['end_fill_v']} issues={r['issues']}")

print()
print(f"ORIGINAL FAILS = {not out[ORIGINAL['id']]['valid']}")
print(f"REPLACEMENT PASSES = {out[REPLACEMENT['id']]['valid']}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "pr004_validation_evidence.json"), "w") as f:
    json.dump(out, f, indent=2)
