"""camera_validator.py — generalized camera proximity + framing validation (PR004).

Operates on arbitrary furniture-mesh AABBs and camera parameters only. Never
references shot IDs or specific mesh names, so it generalizes to any
furniture-sized geometry in any scene.

Rules:
  1. PROXIMITY — every sampled point along a camera path must stay >= MIN_DISTANCE
     meters from the nearest furniture geometry.
  2. FRAMING    — the target arrangement's angular extent (horizontal + vertical)
     must stay within [MIN_FILL, MAX_FILL] of the camera FOV, so the subject is
     readable with surrounding context (rejects both overfill = unreadable flat
     surface, and underfill = subject lost).

Pure-Python (no Blender/mathutils) so it can run standalone for evidence and be
imported inside a Blender script.
"""
import math

MIN_DISTANCE = 2.5   # meters from furniture-sized geometry
MAX_FILL = 0.85      # target angular half-extent / half-FOV above this = overfill
MIN_FILL = 0.15      # below this = subject too small (underfill)


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vlen(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def point_aabb_distance(pt, aabb):
    """Minimum distance from point pt to axis-aligned box aabb = (lo, hi)."""
    lo, hi = aabb
    cx = max(lo[0], min(pt[0], hi[0]))
    cy = max(lo[1], min(pt[1], hi[1]))
    cz = max(lo[2], min(pt[2], hi[2]))
    return vlen(vsub(pt, (cx, cy, cz)))


def nearest_furniture_distance(pt, furniture_aabbs):
    if not furniture_aabbs:
        return float("inf")
    return min(point_aabb_distance(pt, a) for a in furniture_aabbs)


def aabb_center(aabb):
    lo, hi = aabb
    return ((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, (lo[2] + hi[2]) / 2.0)


def aabb_half_extents(aabb):
    lo, hi = aabb
    return ((hi[0] - lo[0]) / 2.0, (hi[1] - lo[1]) / 2.0, (hi[2] - lo[2]) / 2.0)


def framing_fill(aabb, cam_pos, hfov_half_deg, vfov_half_deg):
    """Horizontal + vertical fill fractions of the AABB as seen from cam_pos.

    Uses the AABB center distance and half-width / half-height, which is the
    standard "does this object fit in the frame" approximation for a centered
    subject. Returns (h_fill, v_fill) each in units of the half-FOV.
    """
    c = aabb_center(aabb)
    d = vlen(vsub(c, cam_pos))
    if d <= 0:
        return float("inf"), float("inf")
    hw, _, hh = aabb_half_extents(aabb)
    h_ang = math.degrees(math.atan(hw / d))
    v_ang = math.degrees(math.atan(hh / d))
    hfov_half = max(hfov_half_deg, 1e-6)
    vfov_half = max(vfov_half_deg, 1e-6)
    return h_ang / hfov_half, v_ang / vfov_half


def validate_path(start, end, furniture_aabbs, target_aabb,
                  hfov_half_deg, vfov_half_deg, samples=21):
    """Validate a linear camera path from start to end.

    Returns dict: min_distance_m, end_fill_h, end_fill_v, valid, issues.
    """
    issues = []
    min_dist = float("inf")
    for i in range(samples):
        t = i / (samples - 1)
        pt = (
            start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t,
            start[2] + (end[2] - start[2]) * t,
        )
        d = nearest_furniture_distance(pt, furniture_aabbs)
        min_dist = min(min_dist, d)
        if d < MIN_DISTANCE:
            issues.append("too_close@%d=%.2fm" % (i, d))

    hfill, vfill = framing_fill(target_aabb, end, hfov_half_deg, vfov_half_deg)
    if hfill > MAX_FILL or vfill > MAX_FILL:
        issues.append("overfill_h=%.2f_v=%.2f" % (hfill, vfill))
    if hfill < MIN_FILL:
        issues.append("underfill_h=%.2f" % hfill)

    return {
        "min_distance_m": round(min_dist, 3),
        "end_fill_h": round(hfill, 3),
        "end_fill_v": round(vfill, 3),
        "valid": len(issues) == 0,
        "issues": issues,
    }
