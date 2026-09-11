"""
Vision 5D — Phase 2 Plan Understanding Contracts
All Pydantic models for preprocessing, OCR, CV detection, architectural understanding,
scale, confidence, ambiguity, and canonical architectural graph.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ═══════════════════════════════════════════════════════════
# Preprocessing
# ═══════════════════════════════════════════════════════════

class PreprocessOperation(str, Enum):
    DENOISE = "denoise"
    DESKEW = "deskew"
    CONTRAST = "contrast"
    NORMALIZE = "normalize"
    PERSPECTIVE = "perspective"
    ORIENTATION = "orientation"
    RESOLUTION = "resolution"
    CROP = "crop"
    ENHANCE = "enhance"
    GRAYSCALE = "grayscale"
    BINARIZE = "binarize"
    COLOR_NORMALIZE = "color_normalize"


class PreprocessStep(BaseModel):
    operation: PreprocessOperation
    params: dict = Field(default_factory=dict)
    duration_ms: float = 0.0
    output_hash: Optional[str] = None


class QualityScore(BaseModel):
    overall: float = Field(ge=0.0, le=1.0)
    sharpness: float = Field(ge=0.0, le=1.0)
    contrast: float = Field(ge=0.0, le=1.0)
    noise_level: float = Field(ge=0.0, le=1.0)
    resolution_dpi: int = 0
    usable: bool = False
    issues: list[str] = Field(default_factory=list)


class PreprocessedImage(BaseModel):
    preprocessed_id: UUID = Field(default_factory=uuid4)
    source_asset_id: UUID
    source_page: int = 0
    operations_applied: list[PreprocessStep] = Field(default_factory=list)
    quality: Optional[QualityScore] = None
    width_px: int = 0
    height_px: int = 0
    dpi: int = 150
    format: str = "png"
    storage_locator: str = ""
    content_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# OCR
# ═══════════════════════════════════════════════════════════

class OCREntry(BaseModel):
    """A single recognized text region."""
    entry_id: UUID = Field(default_factory=uuid4)
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)  # x, y, w, h
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    rotation_deg: float = 0.0
    language: str = "eng"
    font_size_estimate: Optional[float] = None
    is_bold: bool = False
    classification: Optional[str] = None  # room_label, dimension, annotation, title, scale, etc.
    source_page: int = 0


class OCRResult(BaseModel):
    ocr_id: UUID = Field(default_factory=uuid4)
    preprocessed_id: UUID
    entries: list[OCREntry] = Field(default_factory=list)
    engine: str = "tesseract"
    engine_version: str = ""
    languages_detected: list[str] = Field(default_factory=list)
    total_confidence: float = 0.0
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Computer Vision Detection
# ═══════════════════════════════════════════════════════════

class DetectionClass(str, Enum):
    WALL = "wall"
    WALL_CENTERLINE = "wall_centerline"
    DOOR = "door"
    DOOR_SWING = "door_swing"
    WINDOW = "window"
    STAIR = "stair"
    COLUMN = "column"
    BEAM = "beam"
    FIXTURE_SINK = "fixture_sink"
    FIXTURE_TOILET = "fixture_toilet"
    FIXTURE_BATHTUB = "fixture_bathtub"
    FIXTURE_SHOWER = "fixture_shower"
    FURNITURE_BED = "furniture_bed"
    FURNITURE_TABLE = "furniture_table"
    FURNITURE_CHAIR = "furniture_chair"
    FURNITURE_SOFA = "furniture_sofa"
    FURNITURE_CABINET = "furniture_cabinet"
    SYMBOL_NORTH = "symbol_north"
    SYMBOL_ELEVATION = "symbol_elevation"
    SYMBOL_SECTION = "symbol_section"
    SYMBOL_ELECTRICAL = "symbol_electrical"
    SYMBOL_PLUMBING = "symbol_plumbing"
    DIMENSION_LINE = "dimension_line"
    DIMENSION_TEXT = "dimension_text"
    GRID_LINE = "grid_line"
    HATCH_REGION = "hatch_region"
    ROOM_REGION = "room_region"
    TEXT_REGION = "text_region"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    rotation_deg: float = 0.0


class Detection(BaseModel):
    detection_id: UUID = Field(default_factory=uuid4)
    class_: DetectionClass = Field(alias="class")
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    centerline: list[tuple[float, float]] = Field(default_factory=list)
    thickness_px: Optional[float] = None
    length_px: Optional[float] = None
    area_px2: Optional[float] = None
    source_model: str = ""
    model_version: str = ""
    feature_vector: list[float] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class DetectionSet(BaseModel):
    detection_set_id: UUID = Field(default_factory=uuid4)
    preprocessed_id: UUID
    detections: list[Detection] = Field(default_factory=list)
    total_detections: int = 0
    models_used: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def by_class(self, cls: DetectionClass) -> list[Detection]:
        return [d for d in self.detections if d.class_ == cls]

    def confident(self, threshold: float = 0.7) -> list[Detection]:
        return [d for d in self.detections if d.confidence >= threshold]


# ═══════════════════════════════════════════════════════════
# Scale
# ═══════════════════════════════════════════════════════════

class ScaleMethod(str, Enum):
    AUTO = "auto"
    DIMENSION_DERIVED = "dimension_derived"
    MANUAL = "manual"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class ScaleCalibration(BaseModel):
    calibration_id: UUID = Field(default_factory=uuid4)
    method: ScaleMethod = ScaleMethod.UNKNOWN
    units: Literal["mm", "cm", "m", "in", "ft"] = "mm"
    pixels_per_unit: float = 0.0
    scale_ratio: str = "1:1"  # e.g., "1:100"
    confidence: float = Field(ge=0.0, le=1.0)
    reference_dimension_mm: Optional[float] = None
    reference_dimension_px: Optional[float] = None
    manual_override: bool = False
    validated: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def px_to_mm(self, px: float) -> float:
        if self.pixels_per_unit <= 0:
            return 0.0
        return px / self.pixels_per_unit

    def mm_to_px(self, mm: float) -> float:
        return mm * self.pixels_per_unit


# ═══════════════════════════════════════════════════════════
# Confidence & Ambiguity
# ═══════════════════════════════════════════════════════════

class ConfidenceLevel(str, Enum):
    HIGH = "high"        # >= 0.85
    MEDIUM = "medium"    # >= 0.60
    LOW = "low"          # >= 0.30
    VERY_LOW = "very_low"  # < 0.30


class ConfidenceAssessment(BaseModel):
    object_id: UUID
    object_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    level: ConfidenceLevel = ConfidenceLevel.LOW
    extraction_method: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    validator_id: Optional[str] = None
    ambiguity_flags: list[str] = Field(default_factory=list)


class ConfidenceReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    preprocessed_id: UUID
    assessments: list[ConfidenceAssessment] = Field(default_factory=list)
    overall_confidence: float = 0.0
    low_confidence_count: int = 0
    needs_review_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Ambiguity(BaseModel):
    ambiguity_id: UUID = Field(default_factory=uuid4)
    region: BoundingBox
    type: Literal["conflicting_ocr", "uncertain_symbol", "broken_wall",
                   "incomplete_room", "missing_label", "unreadable",
                   "scale_conflict", "overlapping_detection"]
    description: str
    severity: Literal["critical", "major", "minor"] = "major"
    candidates: list[str] = Field(default_factory=list)
    requires_review: bool = True


class AmbiguityReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    preprocessed_id: UUID
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    total_ambiguities: int = 0
    critical_count: int = 0
    review_requests: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Architectural Understanding
# ═══════════════════════════════════════════════════════════

class RoomFunction(str, Enum):
    UNKNOWN = "unknown"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    KITCHEN = "kitchen"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    TOILET = "toilet"
    HALLWAY = "hallway"
    CORRIDOR = "corridor"
    STAIRCASE = "staircase"
    ENTRANCE = "entrance"
    GARAGE = "garage"
    STORAGE = "storage"
    UTILITY = "utility"
    OFFICE = "office"
    BALCONY = "balcony"
    TERRACE = "terrace"
    CLOSET = "closet"
    LAUNDRY = "laundry"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    ELEVATOR = "elevator"
    LOBBY = "lobby"
    RECEPTION = "reception"
    CONFERENCE = "conference"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    OTHER = "other"


class Zone(str, Enum):
    PUBLIC = "public"
    SEMI_PUBLIC = "semi_public"
    PRIVATE = "private"
    SERVICE = "service"
    CIRCULATION = "circulation"
    UNKNOWN = "unknown"


class RoomCandidate(BaseModel):
    room_id: UUID = Field(default_factory=uuid4)
    label: Optional[str] = None
    function: RoomFunction = RoomFunction.UNKNOWN
    function_confidence: float = 0.0
    zone: Zone = Zone.UNKNOWN
    area_px2: float = 0.0
    area_m2: Optional[float] = None
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    wall_ids: list[UUID] = Field(default_factory=list)
    opening_ids: list[UUID] = Field(default_factory=list)
    fixture_ids: list[UUID] = Field(default_factory=list)
    adjacent_rooms: list[UUID] = Field(default_factory=list)
    is_exterior: bool = False


class ArchitecturalUnderstanding(BaseModel):
    understanding_id: UUID = Field(default_factory=uuid4)
    preprocessed_id: UUID
    rooms: list[RoomCandidate] = Field(default_factory=list)
    floors_detected: list[str] = Field(default_factory=list)
    building_type: Optional[str] = None
    total_area_m2: Optional[float] = None
    entrance_ids: list[UUID] = Field(default_factory=list)
    circulation_ids: list[UUID] = Field(default_factory=list)
    service_ids: list[UUID] = Field(default_factory=list)
    public_private_ratio: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Canonical Architectural Graph
# ═══════════════════════════════════════════════════════════

class GraphNodeType(str, Enum):
    PAGE = "page"
    FLOOR = "floor"
    ROOM = "room"
    WALL = "wall"
    OPENING = "opening"
    SYMBOL = "symbol"
    LABEL = "label"
    DIMENSION = "dimension"
    ANNOTATION = "annotation"
    FIXTURE = "fixture"
    FURNITURE = "furniture"
    ZONE = "zone"
    BUILDING = "building"


class GraphEdgeType(str, Enum):
    ADJACENT = "adjacent"
    CONTAINS = "contains"
    CONNECTED = "connected"
    BELONGS_TO = "belongs_to"
    ALIGNED_WITH = "aligned_with"
    REFERENCES = "references"
    INTERSECTS = "intersects"
    LABELS = "labels"
    MEASURES = "measures"


class GraphNode(BaseModel):
    node_id: UUID = Field(default_factory=uuid4)
    node_type: GraphNodeType
    label: str = ""
    properties: dict = Field(default_factory=dict)
    detection_ref: Optional[UUID] = None
    confidence: float = 1.0
    source: str = ""


class GraphEdge(BaseModel):
    edge_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    edge_type: GraphEdgeType
    properties: dict = Field(default_factory=dict)
    confidence: float = 1.0


class ArchitecturalGraph(BaseModel):
    """The canonical architectural understanding graph — input to Phase 3."""
    graph_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_asset_id: UUID
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    scale: Optional[ScaleCalibration] = None
    metadata: dict = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_complete: bool = False
    completeness_issues: list[str] = Field(default_factory=list)

    def add_node(self, node: GraphNode) -> GraphNode:
        self.nodes.append(node)
        return node

    def add_edge(self, source_id: UUID, target_id: UUID, edge_type: GraphEdgeType,
                 confidence: float = 1.0, **props) -> GraphEdge:
        edge = GraphEdge(source_id=source_id, target_id=target_id,
                        edge_type=edge_type, confidence=confidence, properties=props)
        self.edges.append(edge)
        return edge

    def nodes_by_type(self, node_type: GraphNodeType) -> list[GraphNode]:
        return [n for n in self.nodes if n.node_type == node_type]

    def edges_by_type(self, edge_type: GraphEdgeType) -> list[GraphEdge]:
        return [e for e in self.edges if e.edge_type == edge_type]

    def room_count(self) -> int:
        return len(self.nodes_by_type(GraphNodeType.ROOM))

    def wall_count(self) -> int:
        return len(self.nodes_by_type(GraphNodeType.WALL))

    def validate_completeness(self) -> list[str]:
        issues = []
        if not self.nodes:
            issues.append("Graph has no nodes")
        if self.room_count() == 0:
            issues.append("No rooms detected")
        if self.wall_count() == 0:
            issues.append("No walls detected")
        if not self.scale or self.scale.confidence < 0.5:
            issues.append("Scale not calibrated with sufficient confidence")
        self.completeness_issues = issues
        self.is_complete = len(issues) == 0
        return issues


# ═══════════════════════════════════════════════════════════
# Pipeline Results
# ═══════════════════════════════════════════════════════════

class PlanUnderstandingResult(BaseModel):
    """Complete Phase 2 pipeline output."""
    result_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_asset_id: UUID
    preprocessed: Optional[PreprocessedImage] = None
    ocr: Optional[OCRResult] = None
    detections: Optional[DetectionSet] = None
    scale: Optional[ScaleCalibration] = None
    understanding: Optional[ArchitecturalUnderstanding] = None
    confidence_report: Optional[ConfidenceReport] = None
    ambiguity_report: Optional[AmbiguityReport] = None
    graph: Optional[ArchitecturalGraph] = None
    pipeline_version: str = "2.0.0"
    total_duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
