"""
Vision 5D — Phase 4 3D Scene Contracts
Canonical domain model for 3D reconstruction, scene objects, materials, lights, cameras.
Coordinate system: mm, horizontal=X/Z, vertical=Y, right-handed.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ═══════════════════════════════════════════════════════════
# 3D Primitives
# ═══════════════════════════════════════════════════════════

class Vec3(BaseModel):
    x: float = 0.0; y: float = 0.0; z: float = 0.0

    def __add__(self, o: "Vec3") -> "Vec3": return Vec3(x=self.x+o.x, y=self.y+o.y, z=self.z+o.z)
    def __sub__(self, o: "Vec3") -> "Vec3": return Vec3(x=self.x-o.x, y=self.y-o.y, z=self.z-o.z)
    def __mul__(self, s: float) -> "Vec3": return Vec3(x=self.x*s, y=self.y*s, z=self.z*s)
    def dot(self, o: "Vec3") -> float: return self.x*o.x + self.y*o.y + self.z*o.z
    def cross(self, o: "Vec3") -> "Vec3": return Vec3(x=self.y*o.z-self.z*o.y, y=self.z*o.x-self.x*o.z, z=self.x*o.y-self.y*o.x)
    def length(self) -> float: return (self.x**2+self.y**2+self.z**2)**0.5
    def normalized(self) -> "Vec3":
        l = self.length()
        return Vec3(x=self.x/l, y=self.y/l, z=self.z/l) if l > 0 else Vec3()
    def to_tuple(self) -> tuple: return (self.x, self.y, self.z)


class Vec2(BaseModel):
    x: float = 0.0; y: float = 0.0
    def to_tuple(self) -> tuple: return (self.x, self.y)


class BBox3(BaseModel):
    min: Vec3 = Field(default_factory=Vec3)
    max: Vec3 = Field(default_factory=Vec3)
    def center(self) -> Vec3: return Vec3(x=(self.min.x+self.max.x)/2, y=(self.min.y+self.max.y)/2, z=(self.min.z+self.max.z)/2)
    def size(self) -> Vec3: return Vec3(x=self.max.x-self.min.x, y=self.max.y-self.min.y, z=self.max.z-self.min.z)


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class SceneObjectType(str, Enum):
    BUILDING = "building"
    LEVEL = "level"
    ROOM_VOLUME = "room_volume"
    WALL_SOLID = "wall_solid"
    FLOOR_SLAB = "floor_slab"
    CEILING_SURFACE = "ceiling_surface"
    ROOF_ELEMENT = "roof_element"
    DOOR_ELEMENT = "door_element"
    WINDOW_ELEMENT = "window_element"
    OPENING_ELEMENT = "opening_element"
    STAIR_ELEMENT = "stair_element"
    COLUMN_ELEMENT = "column_element"
    BEAM_ELEMENT = "beam_element"
    LIGHT = "light"
    CAMERA = "camera"
    FURNITURE_INSTANCE = "furniture_instance"
    SCENE_OBJECT = "scene_object"
    MESH_GROUP = "mesh_group"


class LightType(str, Enum):
    AMBIENT = "ambient"
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"
    AREA = "area"


class CameraType(str, Enum):
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class ValidationClass(str, Enum):
    BLOCKING = "blocking"
    REVIEW = "review"
    ADVISORY = "advisory"


class SceneState(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    STALE = "STALE"
    FAILED = "FAILED"


class MaterialCategory(str, Enum):
    WALL = "wall"
    FLOOR = "floor"
    CEILING = "ceiling"
    ROOF = "roof"
    DOOR = "door"
    WINDOW = "window"
    GLASS = "glass"
    WOOD = "wood"
    METAL = "metal"
    STONE = "stone"
    CONCRETE = "concrete"
    FABRIC = "fabric"
    CUSTOM = "custom"


class FurnitureCategory(str, Enum):
    SEATING = "seating"
    TABLES = "tables"
    STORAGE = "storage"
    BEDS = "beds"
    LIGHTING = "lighting"
    APPLIANCES = "appliances"
    SANITARY = "sanitary"
    DECOR = "decor"
    CUSTOM = "custom"


# ═══════════════════════════════════════════════════════════
# Mesh Data
# ═══════════════════════════════════════════════════════════

class MeshData(BaseModel):
    """Renderable mesh with indexed geometry."""
    mesh_id: UUID = Field(default_factory=uuid4)
    object_id: UUID  # semantic source object
    object_type: SceneObjectType
    vertices: list[float] = Field(default_factory=list)  # [x,y,z, x,y,z, ...]
    indices: list[int] = Field(default_factory=list)     # triangle indices
    normals: list[float] = Field(default_factory=list)    # per-vertex normals
    uvs: list[float] = Field(default_factory=list)        # texture coordinates
    material_id: Optional[UUID] = None
    transform: list[float] = Field(default_factory=lambda: [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1])  # 4x4 matrix
    bbox: Optional[BBox3] = None
    vertex_count: int = 0
    triangle_count: int = 0
    is_valid: bool = True
    validation_issues: list[str] = Field(default_factory=list)
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Materials
# ═══════════════════════════════════════════════════════════

class Material(BaseModel):
    material_id: UUID = Field(default_factory=uuid4)
    name: str = "default"
    category: MaterialCategory = MaterialCategory.CUSTOM
    base_color: tuple[float, float, float, float] = (0.9, 0.9, 0.9, 1.0)
    roughness: float = 0.7
    metallic: float = 0.0
    emissive_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    opacity: float = 1.0
    reflectivity: float = 0.0
    texture_ref: Optional[str] = None
    normal_map_ref: Optional[str] = None
    texture_scale: float = 1.0
    texture_rotation: float = 0.0
    tenant_scope: Optional[UUID] = None  # None = global library
    provenance: str = "default"


# ═══════════════════════════════════════════════════════════
# Lights
# ═══════════════════════════════════════════════════════════

class SceneLight(BaseModel):
    light_id: UUID = Field(default_factory=uuid4)
    light_type: LightType = LightType.DIRECTIONAL
    name: str = "Default Light"
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    position: Vec3 = Field(default_factory=Vec3)
    direction: Vec3 = Field(default_factory=lambda: Vec3(x=0, y=-1, z=0))
    range: float = 0.0
    cone_angle: float = 0.0  # for spot lights
    cast_shadow: bool = True
    visible: bool = True
    temperature: float = 6500.0  # Kelvin
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Cameras
# ═══════════════════════════════════════════════════════════

class Camera(BaseModel):
    camera_id: UUID = Field(default_factory=uuid4)
    camera_type: CameraType = CameraType.PERSPECTIVE
    name: str = "Default Camera"
    position: Vec3 = Field(default_factory=Vec3)
    target: Vec3 = Field(default_factory=Vec3)
    up: Vec3 = Field(default_factory=lambda: Vec3(x=0, y=1, z=0))
    fov: float = 60.0
    near: float = 1.0
    far: float = 100000.0
    zoom: float = 1.0
    model_config = ConfigDict(arbitrary_types_allowed=True)


class CameraView(BaseModel):
    view_id: UUID = Field(default_factory=uuid4)
    name: str = "Default View"
    camera: Camera
    is_default: bool = False


class CameraPathPoint(BaseModel):
    position: Vec3
    target: Vec3
    duration_ms: float = 1000.0


class CameraPath(BaseModel):
    path_id: UUID = Field(default_factory=uuid4)
    name: str = ""
    points: list[CameraPathPoint] = Field(default_factory=list)
    loop: bool = False


# ═══════════════════════════════════════════════════════════
# Furniture Contracts
# ═══════════════════════════════════════════════════════════

class FurnitureAsset(BaseModel):
    asset_id: UUID = Field(default_factory=uuid4)
    name: str
    category: FurnitureCategory = FurnitureCategory.CUSTOM
    source_artifact: Optional[str] = None
    dimensions: Vec3 = Field(default_factory=lambda: Vec3(x=1000, y=800, z=600))
    default_material_id: Optional[UUID] = None
    thumbnail: Optional[str] = None
    content_hash: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FurnitureInstance(BaseModel):
    instance_id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    room_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)  # euler degrees
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1, y=1, z=1))
    color_override: Optional[tuple] = None
    visible: bool = True
    locked: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Floor Finish
# ═══════════════════════════════════════════════════════════

class FloorFinish(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    floor_type: str = "wood"
    base_material_id: Optional[UUID] = None
    color: tuple[float, float, float] = (0.6, 0.4, 0.2)
    texture_ref: Optional[str] = None
    texture_scale: float = 1.0
    texture_rotation: float = 0.0
    tile_length_mm: float = 0.0
    tile_width_mm: float = 0.0
    direction: float = 0.0
    roughness: float = 0.5
    reflectivity: float = 0.1
    room_id: Optional[UUID] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WallFinish(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    color: tuple[float, float, float] = (0.95, 0.95, 0.95)
    roughness: float = 0.9
    wall_id: Optional[UUID] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class CeilingFinish(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    roughness: float = 0.8
    room_id: Optional[UUID] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Semantic 3D Building Objects
# ═══════════════════════════════════════════════════════════

class WallSolid(BaseModel):
    solid_id: UUID = Field(default_factory=uuid4)
    source_wall_id: UUID  # GeometryWall.centerline_id
    vertices: list[Vec3] = Field(default_factory=list)  # 8 vertices of extruded solid
    thickness: float = 0.0
    height: float = 2500.0
    base_elevation: float = 0.0
    is_external: bool = False
    state: str = "inferred"
    bbox: Optional[BBox3] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FloorSlab(BaseModel):
    slab_id: UUID = Field(default_factory=uuid4)
    room_id: Optional[UUID] = None
    vertices: list[Vec3] = Field(default_factory=list)
    elevation: float = 0.0
    thickness: float = 150.0
    area_mm2: float = 0.0
    model_config = ConfigDict(arbitrary_types_allowed=True)


class CeilingSurface(BaseModel):
    ceiling_id: UUID = Field(default_factory=uuid4)
    room_id: Optional[UUID] = None
    vertices: list[Vec3] = Field(default_factory=list)
    elevation: float = 2500.0
    model_config = ConfigDict(arbitrary_types_allowed=True)


class DoorElement(BaseModel):
    door_id: UUID = Field(default_factory=uuid4)
    source_opening_id: UUID
    host_wall_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    width: float = 900.0
    height: float = 2100.0
    sill_height: float = 0.0
    orientation: float = 0.0
    opening_void: list[Vec3] = Field(default_factory=list)  # vertices of the cutout
    type: str = "door"
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WindowElement(BaseModel):
    window_id: UUID = Field(default_factory=uuid4)
    source_opening_id: UUID
    host_wall_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    width: float = 1200.0
    height: float = 1200.0
    sill_height: float = 900.0
    orientation: float = 0.0
    opening_void: list[Vec3] = Field(default_factory=list)
    type: str = "window"
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RoomVolume(BaseModel):
    volume_id: UUID = Field(default_factory=uuid4)
    source_room_id: UUID
    label: Optional[str] = None
    function: Optional[str] = None
    floor_polygon: list[Vec3] = Field(default_factory=list)
    ceiling_polygon: list[Vec3] = Field(default_factory=list)
    floor_area_mm2: float = 0.0
    floor_area_m2: float = 0.0
    perimeter_mm: float = 0.0
    clear_height: float = 2500.0
    volume_mm3: float = 0.0
    floor_elevation: float = 0.0
    wall_ids: list[UUID] = Field(default_factory=list)
    opening_ids: list[UUID] = Field(default_factory=list)
    is_closed: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RoofElement(BaseModel):
    roof_id: UUID = Field(default_factory=uuid4)
    level_id: Optional[UUID] = None
    vertices: list[Vec3] = Field(default_factory=list)
    elevation: float = 2500.0
    thickness: float = 200.0
    type: str = "flat"
    model_config = ConfigDict(arbitrary_types_allowed=True)


class StairElement(BaseModel):
    stair_id: UUID = Field(default_factory=uuid4)
    level_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    dimensions: Vec3 = Field(default_factory=Vec3)
    is_placeholder: bool = True
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ColumnElement(BaseModel):
    column_id: UUID = Field(default_factory=uuid4)
    level_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    dimensions: Vec3 = Field(default_factory=lambda: Vec3(x=300, y=3000, z=300))
    model_config = ConfigDict(arbitrary_types_allowed=True)


class BeamElement(BaseModel):
    beam_id: UUID = Field(default_factory=uuid4)
    level_id: Optional[UUID] = None
    start: Vec3 = Field(default_factory=Vec3)
    end: Vec3 = Field(default_factory=Vec3)
    dimensions: Vec3 = Field(default_factory=lambda: Vec3(x=300, y=500, z=300))
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Level and Scene Hierarchy
# ═══════════════════════════════════════════════════════════

class BuildingLevel(BaseModel):
    level_id: UUID = Field(default_factory=uuid4)
    name: str = "Level 01"
    index: int = 0
    elevation: float = 0.0
    floor_to_floor_height: float = 3000.0
    source_geometry_model_id: Optional[UUID] = None
    rooms: list[RoomVolume] = Field(default_factory=list)
    walls: list[WallSolid] = Field(default_factory=list)
    slabs: list[FloorSlab] = Field(default_factory=list)
    ceilings: list[CeilingSurface] = Field(default_factory=list)
    doors: list[DoorElement] = Field(default_factory=list)
    windows: list[WindowElement] = Field(default_factory=list)
    stairs: list[StairElement] = Field(default_factory=list)
    columns: list[ColumnElement] = Field(default_factory=list)
    beams: list[BeamElement] = Field(default_factory=list)
    scene_objects: list["SceneObject"] = Field(default_factory=list)
    bbox: Optional[BBox3] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SceneObject(BaseModel):
    object_id: UUID = Field(default_factory=uuid4)
    object_type: SceneObjectType
    level_id: Optional[UUID] = None
    position: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1, y=1, z=1))
    visible: bool = True
    metadata: dict = Field(default_factory=dict)
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class SceneValidationIssue(BaseModel):
    issue_id: UUID = Field(default_factory=uuid4)
    object_id: Optional[UUID] = None
    object_type: Optional[SceneObjectType] = None
    code: str = ""
    description: str = ""
    classification: ValidationClass = ValidationClass.ADVISORY
    resolved: bool = False


class SceneValidationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    scene_id: UUID
    issues: list[SceneValidationIssue] = Field(default_factory=list)
    blocking_count: int = 0
    review_count: int = 0
    advisory_count: int = 0
    is_clean: bool = True


# ═══════════════════════════════════════════════════════════
# Scene Statistics
# ═══════════════════════════════════════════════════════════

class SceneStatistics(BaseModel):
    level_count: int = 0
    room_count: int = 0
    wall_count: int = 0
    door_count: int = 0
    window_count: int = 0
    mesh_count: int = 0
    total_floor_area_m2: float = 0.0
    total_room_volume_m3: float = 0.0
    bbox: Optional[BBox3] = None
    vertex_count: int = 0
    triangle_count: int = 0
    validation_issue_count: int = 0
    artifact_size_bytes: int = 0


# ═══════════════════════════════════════════════════════════
# Complete Scene
# ═══════════════════════════════════════════════════════════

class Building3D(BaseModel):
    building_id: UUID = Field(default_factory=uuid4)
    name: str = "Building"
    levels: list[BuildingLevel] = Field(default_factory=list)
    bbox: Optional[BBox3] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Scene3D(BaseModel):
    """The authoritative Phase 4 output — a complete 3D architectural scene."""
    scene_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    source_geometry_model_id: Optional[UUID] = None
    source_geometry_version: int = 1
    source_graph_id: Optional[UUID] = None
    source_graph_version: int = 1
    job_id: Optional[UUID] = None
    pipeline_version: str = "4.0.0"
    version: int = 1
    state: SceneState = SceneState.CREATED
    coordinate_system: str = "mm_right_handed_y_up"
    unit_system: str = "mm"
    building: Optional[Building3D] = None
    materials: list[Material] = Field(default_factory=list)
    lights: list[SceneLight] = Field(default_factory=list)
    cameras: list[Camera] = Field(default_factory=list)
    camera_views: list[CameraView] = Field(default_factory=list)
    furniture_instances: list[FurnitureInstance] = Field(default_factory=list)
    floor_finishes: list[FloorFinish] = Field(default_factory=list)
    wall_finishes: list[WallFinish] = Field(default_factory=list)
    ceiling_finishes: list[CeilingFinish] = Field(default_factory=list)
    meshes: list[MeshData] = Field(default_factory=list)
    scene_objects: list[SceneObject] = Field(default_factory=list)
    validation: Optional[SceneValidationReport] = None
    statistics: Optional[SceneStatistics] = None
    artifact_refs: dict[str, str] = Field(default_factory=dict)  # type→key mapping
    is_complete: bool = False
    completeness_issues: list[str] = Field(default_factory=list)
    lineage: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ScenePipelineResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_geometry_model_id: Optional[UUID] = None
    scene: Optional[Scene3D] = None
    pipeline_version: str = "4.0.0"
    total_duration_ms: float = 0.0
    stages_completed: list[str] = Field(default_factory=list)
    stages_failed: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
