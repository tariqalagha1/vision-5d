"""
Vision 5D — Phase 4 3D Reconstruction Engine
Converts persisted GeometryModel → complete Scene3D with semantic objects, meshes, and validation.
"""
import time, math, structlog
from uuid import UUID, uuid4
from typing import Optional

from packages.geometry.contracts import (
    GeometryModel, FloorGeometry, WallBody, RoomGeometry, Opening, OpeningType,
    Point2D, GeometryState,
)
from packages.scene3d.contracts import (
    Vec3, BBox3, MeshData, Material, SceneLight, Camera, CameraView,
    WallSolid, FloorSlab, CeilingSurface, DoorElement, WindowElement,
    RoomVolume, RoofElement, StairElement, ColumnElement, BeamElement,
    BuildingLevel, Building3D, Scene3D, SceneObject, SceneObjectType,
    FloorFinish, WallFinish, CeilingFinish, FurnitureInstance,
    SceneValidationIssue, SceneValidationReport, SceneStatistics,
    ScenePipelineResult, ValidationClass,
    LightType, CameraType, MaterialCategory, SceneState,
)

logger = structlog.get_logger()

# ── Default dimensions (mm) ──
DEFAULT_WALL_HEIGHT = 2500.0
DEFAULT_SLAB_THICKNESS = 150.0
DEFAULT_CEILING_HEIGHT = 2500.0
DEFAULT_ROOF_THICKNESS = 200.0
DEFAULT_DOOR_HEIGHT = 2100.0
DEFAULT_WINDOW_HEIGHT = 1200.0
DEFAULT_WINDOW_SILL = 900.0


class Scene3DReconstructor:
    """Converts a Phase 3 GeometryModel into a Phase 4 Scene3D."""

    def __init__(self):
        self._meshes: list[MeshData] = []
        self._issues: list[SceneValidationIssue] = []

    def process(self, geometry_model: GeometryModel,
                tenant_id: Optional[UUID] = None,
                workspace_id: Optional[UUID] = None,
                job_id: Optional[UUID] = None) -> ScenePipelineResult:
        t0 = time.time()
        stages_complete = []
        result = ScenePipelineResult(
            project_id=geometry_model.project_id,
            source_geometry_model_id=geometry_model.model_id,
        )

        try:
            # Stage: validate input
            if not geometry_model.floors:
                raise ValueError("GeometryModel has no floors")
            stages_complete.append("validate_input")

            # Stage: create scene
            scene = Scene3D(
                tenant_id=tenant_id, workspace_id=workspace_id,
                project_id=geometry_model.project_id,
                source_geometry_model_id=geometry_model.model_id,
                source_geometry_version=geometry_model.version,
                source_graph_id=geometry_model.source_graph_id,
                source_graph_version=geometry_model.source_graph_version,
                job_id=job_id,
            )
            stages_complete.append("create_scene")

            # Stage: process building
            building = self._build_building(geometry_model)
            scene.building = building
            stages_complete.append("create_levels")

            # Stage: assign materials
            scene.materials = self._default_materials()
            stages_complete.append("assign_materials")

            # Stage: lighting
            scene.lights = self._default_lights(building)
            stages_complete.append("create_default_lighting")

            # Stage: cameras
            scene.cameras, scene.camera_views = self._default_cameras(building)
            stages_complete.append("create_default_cameras")

            # Stage: generate meshes
            scene.meshes = self._meshes
            stages_complete.append("generate_meshes")

            # Stage: default finishes
            scene.floor_finishes = self._default_floor_finishes(building)
            scene.wall_finishes = self._default_wall_finishes(building)
            scene.ceiling_finishes = self._default_ceiling_finishes(building)
            stages_complete.append("assign_finishes")

            # Stage: validate
            scene.validation = self._validate_scene(scene)
            stages_complete.append("validate_scene")

            # Stage: statistics
            scene.statistics = self._compute_statistics(building, scene.meshes)
            stages_complete.append("compute_statistics")

            # Finalize
            scene.state = SceneState.COMPLETE if scene.validation.is_clean else SceneState.VALIDATING
            scene.is_complete = scene.validation.blocking_count == 0
            scene.lineage = self._build_lineage(geometry_model, scene)
            scene.updated_at = scene.created_at

            result.scene = scene
            result.stages_completed = stages_complete
            result.total_duration_ms = (time.time() - t0) * 1000

        except Exception as e:
            import traceback
            logger.error("scene3d_pipeline_failed", error=str(e),
                         traceback=traceback.format_exc())
            result.stages_failed.append(str(e))
            result.total_duration_ms = (time.time() - t0) * 1000

        return result

    # ── Building Construction ──

    def _build_building(self, geo: GeometryModel) -> Building3D:
        building = Building3D(name="Building")
        for fi, floor in enumerate(geo.floors):
            level = self._build_level(floor, fi)
            building.levels.append(level)

        # Compute building bbox
        all_bboxes = [l.bbox for l in building.levels if l.bbox]
        if all_bboxes:
            building.bbox = BBox3(
                min=Vec3(x=min(b.min.x for b in all_bboxes),
                         y=min(b.min.y for b in all_bboxes),
                         z=min(b.min.z for b in all_bboxes)),
                max=Vec3(x=max(b.max.x for b in all_bboxes),
                         y=max(b.max.y for b in all_bboxes),
                         z=max(b.max.z for b in all_bboxes)),
            )
        return building

    def _build_level(self, floor: FloorGeometry, index: int) -> BuildingLevel:
        level = BuildingLevel(
            name=floor.label or f"Level {index+1:02d}",
            index=index,
            elevation=floor.elevation_mm,
            floor_to_floor_height=DEFAULT_WALL_HEIGHT + DEFAULT_SLAB_THICKNESS,
        )

        # Walls → 3D WallSolids
        for wall in floor.walls:
            solid = self._extrude_wall(wall, level.elevation)
            level.walls.append(solid)

        # Rooms → RoomVolumes
        for room in floor.rooms:
            rv = self._create_room_volume(room, level.elevation)
            level.rooms.append(rv)

        # Floors → FloorSlabs
        for room in floor.rooms:
            slab = self._create_floor_slab(room, level.elevation)
            level.slabs.append(slab)

        # Ceilings
        for room in floor.rooms:
            ceil = self._create_ceiling(room, level.elevation)
            level.ceilings.append(ceil)

        # Openings → Door/Window elements
        for op in floor.openings:
            if op.opening_type == OpeningType.DOOR:
                door = self._create_door(op, level.elevation)
                level.doors.append(door)
            elif op.opening_type == OpeningType.WINDOW:
                win = self._create_window(op, level.elevation)
                level.windows.append(win)

        # Roof (top level only)
        if index == 0:  # Single level for now
            roof = self._create_roof(floor, level.elevation + DEFAULT_WALL_HEIGHT)
            level.beams.append(BeamElement())  # placeholder
            # roof is separate — add to scene objects

        # Stairs placeholder
        for _ in floor.stairs:
            level.stairs.append(StairElement(level_id=level.level_id))

        # Columns from floor
        for col_pt in floor.columns:
            level.columns.append(ColumnElement(
                level_id=level.level_id,
                position=Vec3(x=col_pt.x, y=level.elevation, z=col_pt.y),
            ))

        # Compute level bbox
        level.bbox = self._compute_level_bbox(level)
        return level

    # ── Wall Extrusion ──

    def _extrude_wall(self, wall: WallBody, base_elevation: float) -> WallSolid:
        """Extrude a 2D wall body into a 3D solid. Converts x/y (2D mm) to x/z (3D mm),
        with y as vertical axis."""
        h = DEFAULT_WALL_HEIGHT
        vertices_3d = []
        # wall.polygon is [(x1,y1), (x2,y2), ...] in mm (2D floor coords)
        # Map: 2D x→3D x, 2D y→3D z, elevation→3D y
        for pt in wall.polygon:
            vertices_3d.append(Vec3(x=pt.x, y=base_elevation, z=pt.y))
            vertices_3d.append(Vec3(x=pt.x, y=base_elevation + h, z=pt.y))

        solid = WallSolid(
            source_wall_id=wall.centerline_id,
            vertices=vertices_3d,
            thickness=wall.thickness,
            height=h,
            base_elevation=base_elevation,
            is_external=wall.is_external,
            state=wall.state.value if hasattr(wall.state, 'value') else str(wall.state),
        )
        solid.bbox = self._bbox_from_vertices(vertices_3d)

        # Generate mesh for this wall
        self._make_wall_mesh(solid)
        return solid

    def _make_wall_mesh(self, solid: WallSolid):
        """Generate a triangulated mesh for a wall solid from its polygon footprint."""
        if len(solid.vertices) < 6:
            return  # need at least 3 unique 2D points (6 vertices: 3 bottom + 3 top)

        n = len(solid.vertices) // 2  # number of footprint vertices
        vertices = []
        indices = []
        normals = []

        # Build vertices list
        for v in solid.vertices:
            vertices.extend([v.x, v.y, v.z])

        # Triangulate as a "prism": connect bottom and top edges
        for i in range(n):
            b_i = i
            t_i = i + n
            b_next = (i + 1) % n
            t_next = (i + 1) % n + n

            # Triangle 1: bottom[i] → top[i] → bottom[next]
            indices.extend([b_i, t_i, b_next])
            # Triangle 2: top[i] → top[next] → bottom[next]
            indices.extend([t_i, t_next, b_next])

            # Compute face normal for this segment
            v0 = solid.vertices[b_i]
            v1 = solid.vertices[t_i]
            v2 = solid.vertices[b_next]
            e1 = v1 - v0
            e2 = v2 - v0
            nml = e1.cross(e2).normalized()

            for _ in range(3):
                normals.extend([nml.x, nml.y, nml.z])
            for _ in range(3):
                normals.extend([nml.x, nml.y, nml.z])

        # Add top and bottom caps via triangle fan
        self._add_cap_mesh(vertices, indices, normals, range(n), invert=False)   # bottom
        self._add_cap_mesh(vertices, indices, normals, range(n, 2*n), invert=True)  # top

        mesh = MeshData(
            object_id=solid.solid_id,
            object_type=SceneObjectType.WALL_SOLID,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=len(vertices)//3, triangle_count=len(indices)//3,
        )
        mesh.bbox = solid.bbox
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    def _add_cap_mesh(self, vertices, indices, normals, ring_indices, invert=False):
        """Triangulate a polygon cap using a fan from the first vertex."""
        ri = list(ring_indices)
        if len(ri) < 3:
            return
        first = ri[0]
        for i in range(1, len(ri) - 1):
            a, b, c = first, ri[i], ri[i + 1]
            if invert:
                indices.extend([a, c, b])
            else:
                indices.extend([a, b, c])

            # Normal for cap (perpendicular to polygon plane)
            v0 = Vec3(x=vertices[a*3], y=vertices[a*3+1], z=vertices[a*3+2])
            v1 = Vec3(x=vertices[b*3], y=vertices[b*3+1], z=vertices[b*3+2])
            v2 = Vec3(x=vertices[c*3], y=vertices[c*3+1], z=vertices[c*3+2])
            nml = (v1 - v0).cross(v2 - v0).normalized()
            if invert:
                nml = nml * -1.0
            for _ in range(3):
                normals.extend([nml.x, nml.y, nml.z])

    # ── Floor Slabs ──

    def _create_floor_slab(self, room: RoomGeometry, base_elev: float) -> FloorSlab:
        verts = [Vec3(x=p.x, y=base_elev, z=p.y) for p in room.polygon]
        slab = FloorSlab(
            room_id=room.room_id,
            vertices=verts,
            elevation=base_elev,
            thickness=DEFAULT_SLAB_THICKNESS,
            area_mm2=room.area_mm2,
        )
        self._make_floor_mesh(slab)
        return slab

    def _make_floor_mesh(self, slab: FloorSlab):
        if len(slab.vertices) < 3:
            return
        vertices = []
        indices = []
        normals = []

        # Bottom and top faces
        for v in slab.vertices:
            vertices.extend([v.x, v.y, v.z])
        for v in slab.vertices:
            vertices.extend([v.x, v.y + slab.thickness, v.z])

        n = len(slab.vertices)
        # Bottom cap (normal pointing down)
        for i in range(1, n - 1):
            indices.extend([0, i + 1, i])
            for _ in range(3):
                normals.extend([0, -1, 0])

        # Top cap (normal pointing up)
        offset = n
        for i in range(1, n - 1):
            indices.extend([offset, offset + i, offset + i + 1])
            for _ in range(3):
                normals.extend([0, 1, 0])

        # Side walls
        for i in range(n):
            j = (i + 1) % n
            b0, b1 = i, j
            t0, t1 = i + n, j + n
            indices.extend([b0, t0, b1, t0, t1, b1])
            # Normal for this edge
            p0 = slab.vertices[i]
            p1 = slab.vertices[j]
            edge = Vec3(x=p1.x-p0.x, y=0, z=p1.z-p0.z)
            nml = Vec3(x=-edge.z, y=0, z=edge.x).normalized()
            for _ in range(6):
                normals.extend([nml.x, nml.y, nml.z])

        mesh = MeshData(
            object_id=slab.slab_id,
            object_type=SceneObjectType.FLOOR_SLAB,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=len(vertices)//3, triangle_count=len(indices)//3,
            material_id=self._get_material_id("floor"),
        )
        mesh.bbox = BBox3(
            min=Vec3(x=min(v.x for v in slab.vertices), y=slab.elevation, z=min(v.z for v in slab.vertices)),
            max=Vec3(x=max(v.x for v in slab.vertices), y=slab.elevation+slab.thickness, z=max(v.z for v in slab.vertices)),
        )
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    # ── Ceilings ──

    def _create_ceiling(self, room: RoomGeometry, base_elev: float) -> CeilingSurface:
        ceil_elev = base_elev + DEFAULT_CEILING_HEIGHT
        verts = [Vec3(x=p.x, y=ceil_elev, z=p.y) for p in room.polygon]
        ceil = CeilingSurface(room_id=room.room_id, vertices=verts, elevation=ceil_elev)
        self._make_ceiling_mesh(ceil)
        return ceil

    def _make_ceiling_mesh(self, ceil: CeilingSurface):
        if len(ceil.vertices) < 3:
            return
        vertices = []
        indices = []
        normals = []
        for v in ceil.vertices:
            vertices.extend([v.x, v.y, v.z])
        n = len(ceil.vertices)
        for i in range(1, n - 1):
            indices.extend([i + 1, 0, i])  # inverted for downward view
            for _ in range(3):
                normals.extend([0, -1, 0])

        mesh = MeshData(
            object_id=ceil.ceiling_id,
            object_type=SceneObjectType.CEILING_SURFACE,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=n, triangle_count=len(indices)//3,
            material_id=self._get_material_id("ceiling"),
        )
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    # ── Doors ──

    def _create_door(self, op: Opening, base_elev: float) -> DoorElement:
        pos = Vec3(x=op.position.x, y=base_elev + op.sill_height_mm, z=op.position.y)
        # Create door opening void as a box
        hw = op.width_mm / 2
        hh = op.height_mm / 2
        void_verts = [
            Vec3(x=pos.x-hw, y=pos.y-hh, z=pos.z),
            Vec3(x=pos.x+hw, y=pos.y-hh, z=pos.z),
            Vec3(x=pos.x+hw, y=pos.y+hh, z=pos.z),
            Vec3(x=pos.x-hw, y=pos.y+hh, z=pos.z),
        ]
        door = DoorElement(
            source_opening_id=op.opening_id,
            host_wall_id=op.host_wall_id,
            position=pos,
            width=op.width_mm,
            height=op.height_mm or DEFAULT_DOOR_HEIGHT,
            sill_height=op.sill_height_mm,
            orientation=op.orientation_deg,
            opening_void=void_verts,
            type="door",
        )
        self._make_door_mesh(door)
        return door

    def _make_door_mesh(self, door: DoorElement):
        """Simple door leaf as a thin box."""
        hw, hh, hd = door.width/2, door.height/2, 30.0  # half-width, half-height, depth
        px, py, pz = door.position.x, door.position.y, door.position.z
        # Front and back faces of door leaf
        vertices = [
            px-hw, py,    pz-hd,  px+hw, py,    pz-hd,  px+hw, py+door.height, pz-hd,  px-hw, py+door.height, pz-hd,
            px-hw, py,    pz+hd,  px+hw, py,    pz+hd,  px+hw, py+door.height, pz+hd,  px-hw, py+door.height, pz+hd,
        ]
        indices = [0,1,2, 0,2,3,  4,6,5, 4,7,6,  0,4,5, 0,5,1,  2,6,7, 2,7,3,  3,7,4, 3,4,0,  1,5,6, 1,6,2]
        normals = [0,0,-1]*4 + [0,0,1]*4 + [0,-1,0]*2 + [0,1,0]*2 + [-1,0,0]*2 + [1,0,0]*2
        normals = normals + [0,0,-1]*4 + [0,0,1]*4  # pads

        mesh = MeshData(
            object_id=door.door_id,
            object_type=SceneObjectType.DOOR_ELEMENT,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=8, triangle_count=12,
            material_id=self._get_material_id("door"),
        )
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    # ── Windows ──

    def _create_window(self, op: Opening, base_elev: float) -> WindowElement:
        sill_y = base_elev + (op.sill_height_mm or DEFAULT_WINDOW_SILL)
        pos = Vec3(x=op.position.x, y=sill_y, z=op.position.y)
        hw = op.width_mm / 2
        hh = (op.height_mm or DEFAULT_WINDOW_HEIGHT) / 2
        void_verts = [
            Vec3(x=pos.x-hw, y=pos.y, z=pos.z),
            Vec3(x=pos.x+hw, y=pos.y, z=pos.z),
            Vec3(x=pos.x+hw, y=pos.y+hh*2, z=pos.z),
            Vec3(x=pos.x-hw, y=pos.y+hh*2, z=pos.z),
        ]
        win = WindowElement(
            source_opening_id=op.opening_id,
            host_wall_id=op.host_wall_id,
            position=pos,
            width=op.width_mm,
            height=op.height_mm or DEFAULT_WINDOW_HEIGHT,
            sill_height=op.sill_height_mm or DEFAULT_WINDOW_SILL,
            orientation=op.orientation_deg,
            opening_void=void_verts,
            type="window",
        )
        self._make_window_mesh(win)
        return win

    def _make_window_mesh(self, win: WindowElement):
        hw, hh, hd = win.width/2, win.height/2, 50.0
        px, py, pz = win.position.x, win.position.y + hh, win.position.z
        vertices = [
            px-hw, py-hh, pz-hd,  px+hw, py-hh, pz-hd,  px+hw, py+hh, pz-hd,  px-hw, py+hh, pz-hd,
            px-hw, py-hh, pz+hd,  px+hw, py-hh, pz+hd,  px+hw, py+hh, pz+hd,  px-hw, py+hh, pz+hd,
        ]
        indices = [0,1,2, 0,2,3,  4,6,5, 4,7,6,  0,4,5, 0,5,1,  2,6,7, 2,7,3,  3,7,4, 3,4,0,  1,5,6, 1,6,2]
        normals = [0,0,-1]*4 + [0,0,1]*4 + [0,-1,0]*2 + [0,1,0]*2 + [-1,0,0]*2 + [1,0,0]*2

        mesh = MeshData(
            object_id=win.window_id,
            object_type=SceneObjectType.WINDOW_ELEMENT,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=8, triangle_count=12,
            material_id=self._get_material_id("window"),
        )
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    # ── Room Volumes ──

    def _create_room_volume(self, room: RoomGeometry, base_elev: float) -> RoomVolume:
        floor_verts = [Vec3(x=p.x, y=base_elev, z=p.y) for p in room.polygon]
        ceil_verts = [Vec3(x=p.x, y=base_elev + DEFAULT_CEILING_HEIGHT, z=p.y) for p in room.polygon]
        volume = room.area_mm2 * DEFAULT_CEILING_HEIGHT
        return RoomVolume(
            source_room_id=room.room_id,
            label=room.label, function=room.function,
            floor_polygon=floor_verts, ceiling_polygon=ceil_verts,
            floor_area_mm2=room.area_mm2,
            floor_area_m2=room.area_m2(),
            perimeter_mm=room.perimeter_mm,
            clear_height=DEFAULT_CEILING_HEIGHT,
            volume_mm3=volume,
            floor_elevation=base_elev,
            wall_ids=room.wall_ids,
            opening_ids=room.opening_ids,
            is_closed=room.is_closed,
        )

    # ── Roof ──

    def _create_roof(self, floor: FloorGeometry, roof_elev: float) -> RoofElement:
        # Use the floor outline or bounding box of all rooms
        all_pts = []
        for room in floor.rooms:
            all_pts.extend(room.polygon)

        if all_pts:
            from packages.geometry.contracts import BoundingBox2D
            bb = BoundingBox2D.from_points(all_pts)
            verts = [
                Vec3(x=bb.min_x, y=roof_elev, z=bb.min_y),
                Vec3(x=bb.max_x, y=roof_elev, z=bb.min_y),
                Vec3(x=bb.max_x, y=roof_elev, z=bb.max_y),
                Vec3(x=bb.min_x, y=roof_elev, z=bb.max_y),
            ]
        else:
            verts = [Vec3() for _ in range(4)]

        roof = RoofElement(level_id=uuid4(), vertices=verts, elevation=roof_elev,
                           thickness=DEFAULT_ROOF_THICKNESS, type="flat")
        self._make_roof_mesh(roof)
        return roof

    def _make_roof_mesh(self, roof: RoofElement):
        if len(roof.vertices) < 4:
            return
        vertices = []
        for v in roof.vertices:
            vertices.extend([v.x, v.y, v.z])
        for v in roof.vertices:
            vertices.extend([v.x, v.y + roof.thickness, v.z])

        indices = []
        normals = []
        n = len(roof.vertices)
        # Bottom cap
        for i in range(1, n - 1):
            indices.extend([0, i + 1, i])
            for _ in range(3):
                normals.extend([0, -1, 0])
        # Top cap
        offset = n
        for i in range(1, n - 1):
            indices.extend([offset, offset + i, offset + i + 1])
            for _ in range(3):
                normals.extend([0, 1, 0])

        mesh = MeshData(
            object_id=roof.roof_id,
            object_type=SceneObjectType.ROOF_ELEMENT,
            vertices=vertices, indices=indices, normals=normals,
            vertex_count=len(vertices)//3, triangle_count=len(indices)//3,
            material_id=self._get_material_id("roof"),
        )
        self._validate_mesh(mesh)
        self._meshes.append(mesh)

    # ── Mesh Validation ──

    def _validate_mesh(self, mesh: MeshData):
        issues = []
        if mesh.vertex_count == 0:
            issues.append("Empty mesh — no vertices")
        if mesh.triangle_count == 0:
            issues.append("Empty mesh — no triangles")
        if any(math.isnan(v) or math.isinf(v) for v in mesh.vertices):
            issues.append("Non-finite vertex coordinates")
        if not mesh.indices:
            issues.append("No indices")
        if max(mesh.indices or [0]) >= len(mesh.vertices) // 3:
            issues.append("Index out of bounds")

        mesh.is_valid = len(issues) == 0
        mesh.validation_issues = issues

    # ── Bounding Box ──

    def _bbox_from_vertices(self, verts: list[Vec3]) -> BBox3:
        if not verts:
            return BBox3()
        return BBox3(
            min=Vec3(x=min(v.x for v in verts), y=min(v.y for v in verts), z=min(v.z for v in verts)),
            max=Vec3(x=max(v.x for v in verts), y=max(v.y for v in verts), z=max(v.z for v in verts)),
        )

    def _compute_level_bbox(self, level: BuildingLevel) -> Optional[BBox3]:
        all_verts = []
        for w in level.walls:
            all_verts.extend(w.vertices)
        if not all_verts:
            return None
        return self._bbox_from_vertices(all_verts)

    # ── Default Materials ──

    def _get_material_id(self, kind: str) -> UUID:
        """Return stable material IDs for default types."""
        return UUID({
            "wall": "10000000-0000-0000-0000-000000000001",
            "floor": "10000000-0000-0000-0000-000000000002",
            "ceiling": "10000000-0000-0000-0000-000000000003",
            "door": "10000000-0000-0000-0000-000000000004",
            "window": "10000000-0000-0000-0000-000000000005",
            "roof": "10000000-0000-0000-0000-000000000006",
            "glass": "10000000-0000-0000-0000-000000000007",
        }.get(kind, "10000000-0000-0000-0000-000000000000"))

    def _default_materials(self) -> list[Material]:
        return [
            Material(material_id=self._get_material_id("wall"), name="Wall",
                    category=MaterialCategory.WALL, base_color=(0.95, 0.95, 0.95, 1.0), roughness=0.8),
            Material(material_id=self._get_material_id("floor"), name="Floor",
                    category=MaterialCategory.FLOOR, base_color=(0.7, 0.6, 0.5, 1.0), roughness=0.6),
            Material(material_id=self._get_material_id("ceiling"), name="Ceiling",
                    category=MaterialCategory.CEILING, base_color=(1.0, 1.0, 1.0, 1.0), roughness=0.9),
            Material(material_id=self._get_material_id("door"), name="Door",
                    category=MaterialCategory.DOOR, base_color=(0.55, 0.35, 0.15, 1.0), roughness=0.5),
            Material(material_id=self._get_material_id("window"), name="Window Frame",
                    category=MaterialCategory.WINDOW, base_color=(0.8, 0.8, 0.8, 1.0), roughness=0.4, metallic=0.5),
            Material(material_id=self._get_material_id("roof"), name="Roof",
                    category=MaterialCategory.ROOF, base_color=(0.3, 0.3, 0.35, 1.0), roughness=0.7),
            Material(material_id=self._get_material_id("glass"), name="Glass",
                    category=MaterialCategory.GLASS, base_color=(0.85, 0.92, 1.0, 0.4), roughness=0.05, metallic=0.1),
        ]

    # ── Default Lighting ──

    def _default_lights(self, building: Building3D) -> list[SceneLight]:
        lights = []
        # Ambient
        lights.append(SceneLight(
            light_type=LightType.AMBIENT, name="Ambient",
            color=(0.4, 0.4, 0.45,), intensity=0.5, cast_shadow=False,
        ))
        # Directional sun
        bbox = building.bbox
        if bbox:
            center = bbox.center()
            dist = max(bbox.size().x, bbox.size().z) * 2
            lights.append(SceneLight(
                light_type=LightType.DIRECTIONAL, name="Sun",
                color=(1.0, 0.98, 0.92), intensity=1.0,
                position=Vec3(x=center.x + dist, y=center.y + dist, z=center.z + dist),
                direction=Vec3(x=-0.5, y=-1.0, z=-0.5).normalized(),
                cast_shadow=True,
            ))
        else:
            lights.append(SceneLight(
                light_type=LightType.DIRECTIONAL, name="Sun",
                color=(1.0, 0.98, 0.92), intensity=1.0,
                position=Vec3(x=5000, y=8000, z=5000),
                direction=Vec3(x=-0.5, y=-1.0, z=-0.5).normalized(),
            ))
        return lights

    # ── Default Cameras ──

    def _default_cameras(self, building: Building3D) -> tuple[list[Camera], list[CameraView]]:
        bbox = building.bbox
        if bbox:
            center = bbox.center()
            size = bbox.size()
            dist = max(size.x, size.y, size.z) * 2.0
        else:
            center = Vec3()
            dist = 10000.0

        cameras = [
            Camera(camera_id=UUID("20000000-0000-0000-0000-000000000001"),
                   name="Perspective", camera_type=CameraType.PERSPECTIVE,
                   position=Vec3(x=center.x+dist*0.7, y=center.y+dist*0.6, z=center.z+dist*0.7),
                   target=center, fov=45.0),
            Camera(camera_id=UUID("20000000-0000-0000-0000-000000000002"),
                   name="Top View", camera_type=CameraType.PERSPECTIVE,
                   position=Vec3(x=center.x, y=center.y+dist, z=center.z+1),
                   target=center, fov=60.0),
            Camera(camera_id=UUID("20000000-0000-0000-0000-000000000003"),
                   name="Front", camera_type=CameraType.PERSPECTIVE,
                   position=Vec3(x=center.x, y=center.y+dist*0.3, z=center.z+dist),
                   target=center, fov=45.0),
        ]
        views = [
            CameraView(view_id=UUID("30000000-0000-0000-0000-000000000001"),
                      name="Default", camera=cameras[0], is_default=True),
        ]
        return cameras, views

    # ── Default Finishes ──

    def _default_floor_finishes(self, building: Building3D) -> list[FloorFinish]:
        finishes = []
        for level in building.levels:
            for room in level.rooms:
                finishes.append(FloorFinish(
                    room_id=room.source_room_id, floor_type="wood",
                    color=(0.6, 0.4, 0.2), roughness=0.5,
                ))
        return finishes

    def _default_wall_finishes(self, building: Building3D) -> list[WallFinish]:
        finishes = []
        for level in building.levels:
            for wall in level.walls:
                finishes.append(WallFinish(wall_id=wall.source_wall_id))
        return finishes

    def _default_ceiling_finishes(self, building: Building3D) -> list[CeilingFinish]:
        finishes = []
        for level in building.levels:
            for room in level.rooms:
                finishes.append(CeilingFinish(room_id=room.source_room_id))
        return finishes

    # ── Validation ──

    def _validate_scene(self, scene: Scene3D) -> SceneValidationReport:
        issues = []
        if not scene.building or not scene.building.levels:
            issues.append(SceneValidationIssue(code="NO_LEVELS",
                description="Scene has no building levels", classification=ValidationClass.BLOCKING))

        if scene.building:
            for level in scene.building.levels:
                if not level.walls:
                    issues.append(SceneValidationIssue(object_id=level.level_id,
                        object_type=SceneObjectType.LEVEL, code="NO_WALLS",
                        description=f"Level '{level.name}' has no walls"))
                for room in level.rooms:
                    if not room.is_closed:
                        issues.append(SceneValidationIssue(object_id=room.volume_id,
                            object_type=SceneObjectType.ROOM_VOLUME, code="ROOM_NOT_CLOSED",
                            description=f"Room '{room.label}' polygon not closed",
                            classification=ValidationClass.REVIEW))
                    if room.floor_area_mm2 <= 0:
                        issues.append(SceneValidationIssue(object_id=room.volume_id,
                            object_type=SceneObjectType.ROOM_VOLUME, code="ZERO_AREA",
                            description=f"Room '{room.label}' has zero area",
                            classification=ValidationClass.BLOCKING))
                for door in level.doors:
                    if not door.host_wall_id:
                        issues.append(SceneValidationIssue(object_id=door.door_id,
                            object_type=SceneObjectType.DOOR_ELEMENT, code="ORPHAN_DOOR",
                            description="Door has no host wall", classification=ValidationClass.REVIEW))

        # Merge mesh validation issues
        for mesh in scene.meshes:
            for vi in mesh.validation_issues:
                issues.append(SceneValidationIssue(object_id=mesh.object_id,
                    object_type=mesh.object_type, code="MESH_INVALID",
                    description=vi, classification=ValidationClass.BLOCKING))

        blocking = sum(1 for i in issues if i.classification == ValidationClass.BLOCKING)
        review = sum(1 for i in issues if i.classification == ValidationClass.REVIEW)
        advisory = sum(1 for i in issues if i.classification == ValidationClass.ADVISORY)

        return SceneValidationReport(
            scene_id=scene.scene_id, issues=issues,
            blocking_count=blocking, review_count=review, advisory_count=advisory,
            is_clean=blocking == 0,
        )

    # ── Statistics ──

    def _compute_statistics(self, building: Building3D, meshes: list[MeshData]) -> SceneStatistics:
        total_area = 0.0
        total_volume = 0.0
        room_count = 0
        wall_count = 0
        door_count = 0
        window_count = 0

        for level in building.levels:
            room_count += len(level.rooms)
            wall_count += len(level.walls)
            door_count += len(level.doors)
            window_count += len(level.windows)
            for room in level.rooms:
                total_area += room.floor_area_m2
                total_volume += room.volume_mm3 / 1e9  # mm³ → m³

        verts = sum(m.vertex_count for m in meshes)
        tris = sum(m.triangle_count for m in meshes)

        return SceneStatistics(
            level_count=len(building.levels),
            room_count=room_count, wall_count=wall_count,
            door_count=door_count, window_count=window_count,
            mesh_count=len(meshes),
            total_floor_area_m2=round(total_area, 2),
            total_room_volume_m3=round(total_volume, 2),
            bbox=building.bbox,
            vertex_count=verts, triangle_count=tris,
        )

    # ── Lineage ──

    def _build_lineage(self, geo: GeometryModel, scene: Scene3D) -> str:
        parts = []
        if geo.source_graph_id:
            parts.append(f"graph_v{geo.source_graph_version}")
        parts.append(f"geometry_v{geo.version}")
        parts.append(f"scene_v{scene.version}")
        return " → ".join(parts)


scene3d_pipeline = Scene3DReconstructor()
