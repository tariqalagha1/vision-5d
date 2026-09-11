# Adapter Gap Analysis — V5D-PASCAL-SCHEMA-CONFORMANCE-001

## Summary
10 gaps identified: 7 BREAKING, 2 COMPATIBLE, 1 MINOR.

## Gaps
### GAP-001: Scene Format [BREAKING]
- **Proof:** nodes: PascalNode[] (flat array)
- **Pascal:** nodes: Record<AnyNodeId, AnyNode> (string-keyed map)
- **Conversion:** Convert array to map keyed by node.id. Must also provide rootNodeIds array.
- **Data-loss risk:** None — all nodes preserved, just indexed differently.
- **Round-trip impact:** Array order lost but Pascal doesn't preserve it anyway.
- **Migration required:** True

### GAP-002: Root Nodes [BREAKING]
- **Proof:** No rootNodeIds — implicit from building with parentId=null
- **Pascal:** Explicit rootNodeIds: string[]
- **Conversion:** Find all nodes with parentId=null, add their IDs to rootNodeIds array.
- **Data-loss risk:** None — derived from existing data.
- **Round-trip impact:** Requires restoring rootNodeIds on reverse conversion.
- **Migration required:** True

### GAP-003: Wall Geometry [BREAKING]
- **Proof:** position [x,0,z] + custom start_point_2d/end_point_2d in metadata
- **Pascal:** start: [x, y], end: [x, y] — 2D tuples at node level
- **Conversion:** Map start_point_2d → start, end_point_2d → end. Wall position from BaseNode becomes [0,0,0] (child of level).
- **Data-loss risk:** None — geometry preserved exactly.
- **Round-trip impact:** Reverse: derive position from start or midpoint. Custom fields no longer needed.
- **Migration required:** True

### GAP-004: Hierarchy [BREAKING]
- **Proof:** Custom children arrays on building, level
- **Pascal:** parentId on every node + children arrays on building/level/wall
- **Conversion:** Set parentId=levelId on walls/slab/doors/windows. Keep children arrays for building→level, level→children.
- **Data-loss risk:** None — parentId is derivable from children arrays.
- **Round-trip impact:** Both parentId and children must be consistent. rebuild children from parentId if needed.
- **Migration required:** True

### GAP-005: Opening Position [BREAKING]
- **Proof:** Global 3D position [x, sill_height, z] in level coordinates
- **Pascal:** Wall-local 3D position [u_along_wall, v_height, w_offset]
- **Conversion:** Convert global→local: project global point onto wall line. u = distance from wall start. v = sill height. w = 0 (centered on wall).
- **Data-loss risk:** Precision loss from projection (round-trip reversible via wall start + direction).
- **Round-trip impact:** Reverse: local→global using wall start, end, and direction vector.
- **Migration required:** True

### GAP-006: Metadata [COMPATIBLE]
- **Proof:** metadata.vision5d with project_id, source_sha256, dxf_handles, etc.
- **Pascal:** metadata: z.json().optional().default({})
- **Conversion:** No conversion needed — z.json() accepts arbitrary JSON.
- **Data-loss risk:** None — z.json() stores any valid JSON.
- **Round-trip impact:** None — metadata round-trips unchanged.
- **Migration required:** False

### GAP-007: Slab Polygon Axes [MINOR]
- **Proof:** polygon: [[x, y], ...]
- **Pascal:** polygon: z.array(z.tuple([z.number(), z.number()])) — described as [x, z] in docs
- **Conversion:** Map: proof's (x,y) → Pascal's (x, z). Y-axis in proof = Z-axis (north) in Pascal level coords.
- **Data-loss risk:** None — just axis rename.
- **Round-trip impact:** None.
- **Migration required:** True

### GAP-008: Wall Thickness/Height [COMPATIBLE]
- **Proof:** thickness: 0.20, height: 2.70 (hardcoded defaults)
- **Pascal:** thickness: z.number().optional(), height: z.number().optional()
- **Conversion:** No conversion needed — directly mappable.
- **Data-loss risk:** None.
- **Round-trip impact:** None.
- **Migration required:** False

### GAP-009: Site Node [BREAKING]
- **Proof:** No site node — building is root
- **Pascal:** SiteNode is typically root with buildings as children
- **Conversion:** Create a site node, set building.parentId = site.id, rootNodeIds = ['site_...'].
- **Data-loss risk:** None — adds a wrapper node.
- **Round-trip impact:** Strip site node on reverse if not needed.
- **Migration required:** True

### GAP-010: ID Format [MINOR]
- **Proof:** Custom IDs: wall_v5d_000, door_v5d_000, window_v5d_000, building_v5d001
- **Pascal:** objectId('wall') → wall_<nanoid16>, objectId('door') → door_<nanoid16>
- **Conversion:** Regenerate IDs using Pascal's nanoid format OR keep Vision 5D IDs. Both pass Zod validation (z.string()).
- **Data-loss risk:** Low — if we regenerate IDs, need to update all references.
- **Round-trip impact:** If IDs change, stable ID tracking must remap.
- **Migration required:** True


