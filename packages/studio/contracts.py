"""
Vision 5D — Phase 5 Studio Contracts
Edit operations, draft state, studio versions, furniture library, surface finishes.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class StudioEditType(str, Enum):
    ADD_OBJECT = "ADD_OBJECT"
    REMOVE_OBJECT = "REMOVE_OBJECT"
    MOVE_OBJECT = "MOVE_OBJECT"
    ROTATE_OBJECT = "ROTATE_OBJECT"
    SCALE_OBJECT = "SCALE_OBJECT"
    DUPLICATE_OBJECT = "DUPLICATE_OBJECT"
    CHANGE_COLOR = "CHANGE_COLOR"
    CHANGE_MATERIAL = "CHANGE_MATERIAL"
    CHANGE_TEXTURE = "CHANGE_TEXTURE"
    CHANGE_VISIBILITY = "CHANGE_VISIBILITY"
    CHANGE_LOCK_STATE = "CHANGE_LOCK_STATE"
    CHANGE_LIGHT = "CHANGE_LIGHT"
    ADD_LIGHT = "ADD_LIGHT"
    REMOVE_LIGHT = "REMOVE_LIGHT"
    CHANGE_CAMERA = "CHANGE_CAMERA"
    SAVE_CAMERA_VIEW = "SAVE_CAMERA_VIEW"
    CREATE_CAMERA_PATH = "CREATE_CAMERA_PATH"
    CHANGE_FLOOR_FINISH = "CHANGE_FLOOR_FINISH"
    CHANGE_WALL_FINISH = "CHANGE_WALL_FINISH"
    CHANGE_CEILING_FINISH = "CHANGE_CEILING_FINISH"
    GROUP_OBJECTS = "GROUP_OBJECTS"
    UNGROUP_OBJECTS = "UNGROUP_OBJECTS"
    RENAME_OBJECT = "RENAME_OBJECT"


class StudioState(str, Enum):
    DRAFT = "DRAFT"
    COMMITTED = "COMMITTED"
    BRANCHED = "BRANCHED"


class FloorType(str, Enum):
    CERAMIC = "ceramic"; PORCELAIN = "porcelain"; MARBLE = "marble"
    GRANITE = "granite"; WOOD = "wood"; LAMINATE = "laminate"
    VINYL = "vinyl"; CARPET = "carpet"; CONCRETE = "concrete"
    EPOXY = "epoxy"; STONE = "stone"


class PlacementIssueSeverity(str, Enum):
    BLOCKING = "blocking"; WARNING = "warning"; ADVISORY = "advisory"


# ── Edit Operation ──

class StudioEditOperation(BaseModel):
    operation_id: UUID = Field(default_factory=uuid4)
    studio_version_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    target_object_id: Optional[UUID] = None
    object_type: Optional[str] = None
    operation_type: StudioEditType
    before_state: dict = Field(default_factory=dict)
    after_state: dict = Field(default_factory=dict)
    sequence: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_undone: bool = False


class UndoRedoState(BaseModel):
    operations: list[StudioEditOperation] = Field(default_factory=list)
    undo_stack: list[int] = Field(default_factory=list)
    redo_stack: list[int] = Field(default_factory=list)
    current_sequence: int = 0
    max_history: int = 200


# ── Object State ──

class StudioObjectState(BaseModel):
    object_id: UUID
    object_type: str
    label: str = ""
    position: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    scale: tuple[float, float, float] = (1, 1, 1)
    visible: bool = True
    locked: bool = False
    room_id: Optional[UUID] = None
    level_id: Optional[UUID] = None
    color_override: Optional[tuple[float, float, float]] = None
    material_override: Optional[str] = None
    properties: dict = Field(default_factory=dict)


# ── Material Override ──

class MaterialOverride(BaseModel):
    override_id: UUID = Field(default_factory=uuid4)
    object_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    base_color: tuple[float, float, float, float] = (0.9, 0.9, 0.9, 1.0)
    roughness: float = 0.7
    metallic: float = 0.0
    opacity: float = 1.0
    emissive_color: tuple[float, float, float] = (0, 0, 0)
    texture_scale: float = 1.0
    texture_rotation: float = 0.0
    reflectivity: float = 0.0
    normal_map_ref: Optional[str] = None
    apply_to: str = "object"  # object | room | level | category


# ── Light State ──

class LightState(BaseModel):
    light_id: UUID = Field(default_factory=uuid4)
    name: str = "Light"
    light_type: str = "directional"
    color: tuple[float, float, float] = (1, 1, 1)
    intensity: float = 1.0
    position: tuple[float, float, float] = (0, 5000, 0)
    direction: tuple[float, float, float] = (0, -1, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    temperature: float = 6500.0
    range: float = 0.0
    cone_angle: float = 0.0
    cast_shadow: bool = True
    visible: bool = True


# ── Camera State ──

class CameraViewState(BaseModel):
    view_id: UUID = Field(default_factory=uuid4)
    name: str = "View"
    camera_type: str = "perspective"
    position: tuple[float, float, float] = (5000, 6000, 5000)
    target: tuple[float, float, float] = (0, 1200, 0)
    direction: tuple[float, float, float] = (0, 0, 0)
    fov: float = 50.0
    zoom: float = 1.0
    near: float = 1.0
    far: float = 100000.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CameraPathPoint(BaseModel):
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    duration_ms: float = 2000.0
    easing: str = "linear"
    pause_ms: float = 0.0


class CameraPathState(BaseModel):
    path_id: UUID = Field(default_factory=uuid4)
    name: str = "Path"
    points: list[CameraPathPoint] = Field(default_factory=list)
    loop: bool = False
    speed: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Furniture ──

class FurnitureLibraryItem(BaseModel):
    asset_id: UUID = Field(default_factory=uuid4)
    name: str
    category: str = "generic"
    subcategory: str = ""
    dimensions: tuple[float, float, float] = (1000, 800, 600)  # w, h, d mm
    thumbnail: Optional[str] = None
    source_artifact: Optional[str] = None
    default_material: Optional[str] = None
    content_hash: Optional[str] = None
    description: str = ""


class FurnitureInstanceState(BaseModel):
    instance_id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    room_id: Optional[UUID] = None
    level_id: Optional[UUID] = None
    position: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    scale: tuple[float, float, float] = (1, 1, 1)
    color_override: Optional[tuple[float, float, float]] = None
    material_override: Optional[str] = None
    visible: bool = True
    locked: bool = False
    label: str = ""


# ── Surface Finishes ──

class FloorFinishState(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    room_id: Optional[UUID] = None
    floor_type: FloorType = FloorType.WOOD
    color: tuple[float, float, float] = (0.6, 0.4, 0.2)
    texture_ref: Optional[str] = None
    texture_scale: float = 1.0
    texture_rotation: float = 0.0
    tile_length_mm: float = 0.0
    tile_width_mm: float = 0.0
    direction: float = 0.0
    roughness: float = 0.5
    reflectivity: float = 0.1


class WallFinishState(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    wall_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    color: tuple[float, float, float] = (0.95, 0.95, 0.95)
    texture_ref: Optional[str] = None
    texture_scale: float = 1.0
    texture_rotation: float = 0.0
    roughness: float = 0.9
    reflectivity: float = 0.05


class CeilingFinishState(BaseModel):
    finish_id: UUID = Field(default_factory=uuid4)
    room_id: Optional[UUID] = None
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    texture_ref: Optional[str] = None
    reflectivity: float = 0.1
    roughness: float = 0.8


# ── Placement Validation ──

class PlacementIssue(BaseModel):
    issue_id: UUID = Field(default_factory=uuid4)
    object_id: UUID
    severity: PlacementIssueSeverity = PlacementIssueSeverity.WARNING
    code: str = ""
    message: str = ""
    suggested_action: str = ""
    resolved: bool = False


# ── Studio Draft ──

class StudioDraft(BaseModel):
    draft_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    source_scene_id: Optional[UUID] = None
    source_scene_version: int = 1
    state: StudioState = StudioState.DRAFT
    object_states: list[StudioObjectState] = Field(default_factory=list)
    lights: list[LightState] = Field(default_factory=list)
    cameras: list[CameraViewState] = Field(default_factory=list)
    camera_paths: list[CameraPathState] = Field(default_factory=list)
    furniture_instances: list[FurnitureInstanceState] = Field(default_factory=list)
    floor_finishes: list[FloorFinishState] = Field(default_factory=list)
    wall_finishes: list[WallFinishState] = Field(default_factory=list)
    ceiling_finishes: list[CeilingFinishState] = Field(default_factory=list)
    material_overrides: list[MaterialOverride] = Field(default_factory=list)
    edit_operations: UndoRedoState = Field(default_factory=UndoRedoState)
    placement_issues: list[PlacementIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    save_counter: int = 0


# ── Studio Version ──

class StudioSceneVersion(BaseModel):
    version_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    source_scene_id: Optional[UUID] = None
    source_scene_version: int = 1
    parent_studio_version: Optional[UUID] = None
    version_number: int = 1
    name: str = ""
    description: str = ""
    state: StudioState = StudioState.COMMITTED
    edit_count: int = 0
    draft_snapshot: dict = Field(default_factory=dict)
    lineage: str = ""
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── API Models ──

class StudioDraftLoad(BaseModel):
    draft: Optional[StudioDraft] = None
    source_scene: Optional[dict] = None
    scene_id: Optional[UUID] = None
    is_new: bool = True


class EditOperationRequest(BaseModel):
    operations: list[StudioEditOperation]
    draft_id: Optional[UUID] = None


class CommitVersionRequest(BaseModel):
    draft_id: UUID
    name: str = ""
    description: str = ""


class FurniturePlaceRequest(BaseModel):
    draft_id: UUID
    asset_id: UUID
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0, 0, 0)
    room_id: Optional[UUID] = None


class TransformRequest(BaseModel):
    draft_id: UUID
    object_id: UUID
    position: Optional[tuple[float, float, float]] = None
    rotation: Optional[tuple[float, float, float]] = None
    scale: Optional[tuple[float, float, float]] = None


class FinishUpdateRequest(BaseModel):
    draft_id: UUID
    finish_type: str  # floor, wall, ceiling
    room_id: Optional[UUID] = None
    wall_id: Optional[UUID] = None
    color: Optional[tuple[float, float, float]] = None
    floor_type: Optional[str] = None
    texture_scale: Optional[float] = None
    roughness: Optional[float] = None
    reflectivity: Optional[float] = None


class LightUpdateRequest(BaseModel):
    draft_id: UUID
    light_id: Optional[UUID] = None
    action: str  # add, update, remove
    color: Optional[tuple[float, float, float]] = None
    intensity: Optional[float] = None
    position: Optional[tuple[float, float, float]] = None
    direction: Optional[tuple[float, float, float]] = None
    light_type: Optional[str] = None
    name: Optional[str] = None


class CameraViewUpdateRequest(BaseModel):
    draft_id: UUID
    view_id: Optional[UUID] = None
    name: Optional[str] = None
    position: Optional[tuple[float, float, float]] = None
    target: Optional[tuple[float, float, float]] = None
    fov: Optional[float] = None


class CameraPathUpdateRequest(BaseModel):
    draft_id: UUID
    path_id: Optional[UUID] = None
    name: Optional[str] = None
    points: Optional[list[CameraPathPoint]] = None
    action: str = "create"  # create, update, delete
