# Coordinate Conversion Specification

## Vision 5D → Pascal
- Vision 5D: X (east), Y (north), Z (up) — meters
- Pascal: X (east), Y (up), Z (north) — meters
- Conversion: V5D(x, y, z) → Pascal(x, z, y)
- Wall start/end: 2D [x, y] tuples directly, no conversion needed (both in level XY plane)

## Opening: Global → Wall-Local
- Global: [x_global, y_global, sill_height]
- Wall-local: [u_along_wall, v_height, w_offset]
- u = dot(global_pos - wall_start, wall_direction)
- v = sill_height or door height from floor
- w = 0 (centered on wall mid-plane)
