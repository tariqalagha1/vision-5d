# Opening Position Conversion Specification

## Pascal Wall-Local Convention
position: [u, v, w]
- u: distance along wall from start point (meters)
- v: height from floor (meters) — sill height for windows
- w: offset from wall mid-plane (meters) — 0 = centered

## Door Convention
- position: [midpoint_u, 0, 0]
- v = 0 (floor level)
- width = 0.9m, height = 2.1m (defaults)

## Window Convention
- position: [midpoint_u, sill_height, 0]
- v = sill height (e.g., 1.0m)
- width = 1.5m, height = 1.2m (defaults)

## Global↔Local Reversibility
- local→global: global = wall_start + u * wall_direction, y = v, offset = 0
- Requires wall start/end and direction vector for reverse
