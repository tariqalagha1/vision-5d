"""
Vision 5D — Phase 3 Geometry Engine Contracts
All Pydantic models for geometric primitives, wall reconstruction, room polygons,
openings, topology, constraints, repair, validation, and the editable floor plan model.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ═══════════════════════════════════════════════════════════
# Coordinate Systems
# ═══════════════════════════════════════════════════════════

class CoordSystem(str, Enum):
    IMAGE = "image"           # pixel coordinates (origin top-left)
    NORMALIZED = "normalized" # 0-1 range
    WORLD = "world"           # real-world mm
    FLOOR_LOCAL = "floor_local"
    BUILDING_GLOBAL = "building_global"


class CoordTransform(BaseModel):
    """Explicit reversible coordinate transformation."""
    transform_id: UUID = Field(default_factory=uuid4)
    from_system: CoordSystem
    to_system: CoordSystem
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    rotation_deg: float = 0.0
    shear_x: float = 0.0
    shear_y: float = 0.0
    is_identity: bool = False

    def to_matrix_3x3(self) -> list[list[float]]:
        import math
        r = math.radians(self.rotation_deg)
        cos_r, sin_r = math.cos(r), math.sin(r)
        return [
            [self.scale_x * cos_r + self.shear_x * sin_r, -self.scale_x * sin_r + self.shear_x * cos_r, self.offset_x],
            [self.scale_y * sin_r + self.shear_y * cos_r, self.scale_y * cos_r - self.shear_y * sin_r, self.offset_y],
            [0, 0, 1]
        ]


class Point2D(BaseModel):
    x: float
    y: float

    def __add__(self, other: "Point2D") -> "Point2D": return Point2D(x=self.x+other.x, y=self.y+other.y)
    def __sub__(self, other: "Point2D") -> "Point2D": return Point2D(x=self.x-other.x, y=self.y-other.y)
    def __mul__(self, s: float) -> "Point2D": return Point2D(x=self.x*s, y=self.y*s)
    def __truediv__(self, s: float) -> "Point2D": return Point2D(x=self.x/s, y=self.y/s)
    def dot(self, other: "Point2D") -> float: return self.x*other.x + self.y*other.y
    def cross(self, other: "Point2D") -> float: return self.x*other.y - self.y*other.x
    def length(self) -> float: return (self.x**2 + self.y**2)**0.5
    def distance_to(self, other: "Point2D") -> float: return (self - other).length()
    def normalized(self) -> "Point2D":
        l = self.length()
        return Point2D(x=self.x/l, y=self.y/l) if l > 0 else Point2D(x=0, y=0)
    def rotate(self, angle_deg: float, origin: "Point2D" = None) -> "Point2D":
        import math
        r = math.radians(angle_deg)
        ox, oy = (origin.x, origin.y) if origin else (0, 0)
        dx, dy = self.x - ox, self.y - oy
        return Point2D(x=ox + dx*math.cos(r) - dy*math.sin(r), y=oy + dx*math.sin(r) + dy*math.cos(r))
    def angle_deg(self) -> float:
        import math
        return math.degrees(math.atan2(self.y, self.x))
    def to_tuple(self) -> tuple[float, float]: return (self.x, self.y)


class Line2D(BaseModel):
    start: Point2D
    end: Point2D

    def length(self) -> float: return self.start.distance_to(self.end)
    def midpoint(self) -> Point2D: return Point2D(x=(self.start.x+self.end.x)/2, y=(self.start.y+self.end.y)/2)
    def direction(self) -> Point2D: return (self.end - self.start).normalized()
    def angle_deg(self) -> float:
        import math
        return math.degrees(math.atan2(self.end.y-self.start.y, self.end.x-self.start.x))
    def perpendicular(self) -> Point2D:
        d = self.direction()
        return Point2D(x=-d.y, y=d.x)
    def offset_line(self, offset: float) -> "Line2D":
        perp = self.perpendicular()
        return Line2D(start=self.start + perp*offset, end=self.end + perp*offset)
    def distance_to_point(self, pt: Point2D) -> float:
        v = self.end - self.start
        w = pt - self.start
        t = max(0, min(1, w.dot(v) / v.dot(v))) if v.dot(v) > 0 else 0
        return pt.distance_to(self.start + v*t)
    def intersection(self, other: "Line2D") -> Optional[Point2D]:
        p, r = self.start, self.end - self.start
        q, s = other.start, other.end - other.start
        cross_rs = r.cross(s)
        if abs(cross_rs) < 1e-10: return None
        t = (q - p).cross(s) / cross_rs
        u = (q - p).cross(r) / cross_rs
        if 0 <= t <= 1 and 0 <= u <= 1:
            return p + r*t
        return None
    def extend_to_intersection(self, other: "Line2D") -> Optional[Point2D]:
        """Extend this line (infinite) to intersect with other."""
        p, r = self.start, self.end - self.start
        q, s = other.start, other.end - other.start
        cross_rs = r.cross(s)
        if abs(cross_rs) < 1e-10: return None
        t = (q - p).cross(s) / cross_rs
        return p + r*t


class Polygon2D(BaseModel):
    vertices: list[Point2D] = Field(default_factory=list)

    def area(self) -> float:
        if len(self.vertices) < 3: return 0.0
        a = 0.0
        for i in range(len(self.vertices)):
            j = (i+1) % len(self.vertices)
            a += self.vertices[i].x * self.vertices[j].y
            a -= self.vertices[j].x * self.vertices[i].y
        return abs(a) / 2.0

    def perimeter(self) -> float:
        if len(self.vertices) < 2: return 0.0
        p = 0.0
        for i in range(len(self.vertices)):
            p += self.vertices[i].distance_to(self.vertices[(i+1)%len(self.vertices)])
        return p

    def centroid(self) -> Point2D:
        if len(self.vertices) < 3: return Point2D(x=0, y=0)
        a = self.area()
        if a < 1e-10: return Point2D(x=0, y=0)
        cx, cy = 0.0, 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i+1) % n
            f = self.vertices[i].x*self.vertices[j].y - self.vertices[j].x*self.vertices[i].y
            cx += (self.vertices[i].x+self.vertices[j].x)*f
            cy += (self.vertices[i].y+self.vertices[j].y)*f
        return Point2D(x=cx/(6*a), y=cy/(6*a))

    def contains_point(self, pt: Point2D) -> bool:
        """Ray casting algorithm."""
        n = len(self.vertices)
        if n < 3: return False
        inside = False
        j = n-1
        for i in range(n):
            vi, vj = self.vertices[i], self.vertices[j]
            if ((vi.y > pt.y) != (vj.y > pt.y)) and                (pt.x < (vj.x-vi.x)*(pt.y-vi.y)/(vj.y-vi.y) + vi.x):
                inside = not inside
            j = i
        return inside

    def is_valid(self) -> bool:
        """Check for self-intersection."""
        if len(self.vertices) < 3: return False
        n = len(self.vertices)
        for i in range(n):
            e1 = Line2D(start=self.vertices[i], end=self.vertices[(i+1)%n])
            for j in range(i+2, n):
                if j == (i+1)%n or i == (j+1)%n: continue
                e2 = Line2D(start=self.vertices[j], end=self.vertices[(j+1)%n])
                if e1.intersection(e2): return False
        return True


class BoundingBox2D(BaseModel):
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0

    def width(self) -> float: return self.max_x - self.min_x
    def height(self) -> float: return self.max_y - self.min_y
    def center(self) -> Point2D: return Point2D(x=(self.min_x+self.max_x)/2, y=(self.min_y+self.max_y)/2)
    def contains(self, pt: Point2D) -> bool: return self.min_x <= pt.x <= self.max_x and self.min_y <= pt.y <= self.max_y
    def expand(self, amount: float) -> "BoundingBox2D":
        return BoundingBox2D(min_x=self.min_x-amount, min_y=self.min_y-amount,
                             max_x=self.max_x+amount, max_y=self.max_y+amount)

    @classmethod
    def from_points(cls, pts: list[Point2D]) -> "BoundingBox2D":
        if not pts: return cls()
        return cls(min_x=min(p.x for p in pts), min_y=min(p.y for p in pts),
                   max_x=max(p.x for p in pts), max_y=max(p.y for p in pts))


# ═══════════════════════════════════════════════════════════
# Geometry State Classification
# ═══════════════════════════════════════════════════════════

class GeometryState(str, Enum):
    CONFIRMED = "confirmed"       # verified from source
    INFERRED = "inferred"         # algorithmically deduced
    PROVISIONAL = "provisional"   # best guess, flag for review
    AMBIGUOUS = "ambiguous"       # multiple candidates
    MANUALLY_CORRECTED = "manually_corrected"
    INVALID = "invalid"
    UNRESOLVED = "unresolved"


class ConstraintStrength(str, Enum):
    REQUIRED = "required"
    STRONG = "strong"
    PREFERRED = "preferred"
    WEAK = "weak"
    ADVISORY = "advisory"


class JunctionType(str, Enum):
    L = "L"           # two walls meet at 90°
    T = "T"           # wall ends at another wall
    X = "X"           # two walls cross
    CORNER = "corner"  # two walls at corner angle
    ENDPOINT = "endpoint"  # wall terminates free
    MULTI = "multi"    # 3+ walls meet


# ═══════════════════════════════════════════════════════════
# Wall Geometry
# ═══════════════════════════════════════════════════════════

class WallCenterline(BaseModel):
    centerline_id: UUID = Field(default_factory=uuid4)
    points: list[Point2D] = Field(default_factory=list)  # ordered centerline points
    graph_node_ref: Optional[UUID] = None  # Phase 2 GraphNode.node_id
    detection_ref: Optional[UUID] = None   # Phase 2 Detection
    confidence: float = 1.0
    state: GeometryState = GeometryState.INFERRED
    is_external: bool = False
    source: str = ""

    def as_lines(self) -> list[Line2D]:
        return [Line2D(start=self.points[i], end=self.points[i+1]) for i in range(len(self.points)-1)]

    def length(self) -> float:
        return sum(l.length() for l in self.as_lines())

    def midpoint(self) -> Point2D:
        if not self.points: return Point2D(x=0,y=0)
        return Point2D(x=sum(p.x for p in self.points)/len(self.points),
                       y=sum(p.y for p in self.points)/len(self.points))


class WallThickness(BaseModel):
    thickness_id: UUID = Field(default_factory=uuid4)
    centerline_id: UUID
    value_mm: float = 0.0
    unit: str = "mm"
    confidence: float = 0.0
    method: str = ""  # paired_lines, scale_derived, convention, user
    evidence: list[str] = Field(default_factory=list)
    override: bool = False

    @property
    def half(self) -> float: return self.value_mm / 2.0


class WallBody(BaseModel):
    body_id: UUID = Field(default_factory=uuid4)
    centerline_id: UUID
    centerline: list[Point2D] = Field(default_factory=list)
    face_left: list[Point2D] = Field(default_factory=list)
    face_right: list[Point2D] = Field(default_factory=list)
    thickness: float = 0.0  # mm
    polygon: list[Point2D] = Field(default_factory=list)  # closed polygon of wall body
    is_external: bool = False
    confidence: float = 1.0
    state: GeometryState = GeometryState.INFERRED
    source_graph_ref: Optional[UUID] = None


class WallJunction(BaseModel):
    junction_id: UUID = Field(default_factory=uuid4)
    junction_type: JunctionType
    position: Point2D
    wall_ids: list[UUID] = Field(default_factory=list)  # centerline_ids
    confidence: float = 1.0
    state: GeometryState = GeometryState.INFERRED


# ═══════════════════════════════════════════════════════════
# Opening Geometry
# ═══════════════════════════════════════════════════════════

class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    UNKNOWN = "unknown"


class OpeningSwing(str, Enum):
    INWARD = "inward"
    OUTWARD = "outward"
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"
    SLIDING = "sliding"
    UNKNOWN = "unknown"


class Opening(BaseModel):
    opening_id: UUID = Field(default_factory=uuid4)
    opening_type: OpeningType = OpeningType.UNKNOWN
    host_wall_id: Optional[UUID] = None  # centerline_id
    position_along_wall: float = 0.0  # 0-1 normalized along centerline
    position: Point2D = Field(default_factory=lambda: Point2D(x=0,y=0))
    width_mm: float = 0.0
    height_mm: float = 2100.0  # standard door height default
    orientation_deg: float = 0.0
    swing: OpeningSwing = OpeningSwing.UNKNOWN
    sill_height_mm: float = 0.0  # for windows
    graph_node_ref: Optional[UUID] = None
    detection_ref: Optional[UUID] = None
    confidence: float = 1.0
    state: GeometryState = GeometryState.INFERRED
    connects_room_a: Optional[UUID] = None
    connects_room_b: Optional[UUID] = None
    is_valid: bool = True
    validation_issues: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Room Geometry
# ═══════════════════════════════════════════════════════════

class RoomGeometry(BaseModel):
    room_id: UUID = Field(default_factory=uuid4)
    label: Optional[str] = None
    function: Optional[str] = None
    polygon: list[Point2D] = Field(default_factory=list)
    area_mm2: float = 0.0
    perimeter_mm: float = 0.0
    centroid: Point2D = Field(default_factory=lambda: Point2D(x=0,y=0))
    wall_ids: list[UUID] = Field(default_factory=list)  # centerline_ids forming boundary
    opening_ids: list[UUID] = Field(default_factory=list)
    fixture_ids: list[UUID] = Field(default_factory=list)
    adjacent_room_ids: list[UUID] = Field(default_factory=list)
    graph_node_ref: Optional[UUID] = None
    confidence: float = 1.0
    state: GeometryState = GeometryState.INFERRED
    is_closed: bool = False
    has_holes: bool = False
    is_exterior: bool = False
    validation_issues: list[str] = Field(default_factory=list)

    def area_m2(self) -> float: return self.area_mm2 / 1_000_000

    def validate_closure(self) -> bool:
        self.is_closed = len(self.polygon) >= 3 and self.polygon[0].distance_to(self.polygon[-1]) < 1.0
        return self.is_closed


# ═══════════════════════════════════════════════════════════
# Floor Geometry
# ═══════════════════════════════════════════════════════════

class FloorGeometry(BaseModel):
    floor_id: UUID = Field(default_factory=uuid4)
    floor_number: int = 0
    label: str = "Ground Floor"
    elevation_mm: float = 0.0
    outline: list[Point2D] = Field(default_factory=list)
    walls: list[WallBody] = Field(default_factory=list)
    rooms: list[RoomGeometry] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    columns: list[Point2D] = Field(default_factory=list)
    stairs: list[dict] = Field(default_factory=list)
    fixtures: list[dict] = Field(default_factory=list)
    junctions: list[WallJunction] = Field(default_factory=list)
    scale_px_per_mm: float = 0.0
    units: str = "mm"
    source_graph_ref: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════
# Topology
# ═══════════════════════════════════════════════════════════

class TopologyRelation(str, Enum):
    CONTAINED_IN = "contained_in"
    ADJACENT_TO = "adjacent_to"
    CONNECTED_BY = "connected_by"
    SHARED_BOUNDARY = "shared_boundary"
    INSIDE = "inside"
    OUTSIDE = "outside"


class TopologyEdge(BaseModel):
    edge_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relation: TopologyRelation
    shared_wall_ids: list[UUID] = Field(default_factory=list)
    shared_opening_ids: list[UUID] = Field(default_factory=list)
    confidence: float = 1.0


class TopologyGraph(BaseModel):
    topology_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    edges: list[TopologyEdge] = Field(default_factory=list)
    disconnected_components: list[list[UUID]] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    is_consistent: bool = True


# ═══════════════════════════════════════════════════════════
# Constraints
# ═══════════════════════════════════════════════════════════

class ConstraintType(str, Enum):
    COINCIDENT = "coincident"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    COLLINEAR = "collinear"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    EQUAL_LENGTH = "equal_length"
    EQUAL_THICKNESS = "equal_thickness"
    FIXED_DISTANCE = "fixed_distance"
    FIXED_ANGLE = "fixed_angle"
    SHARED_ENDPOINT = "shared_endpoint"
    ATTACHED_OPENING = "attached_opening"
    CLOSED_POLYGON = "closed_polygon"
    NON_OVERLAP = "non_overlap"
    CONTAINMENT = "containment"
    ALIGNMENT = "alignment"
    SYMMETRY = "symmetry"


class Constraint(BaseModel):
    constraint_id: UUID = Field(default_factory=uuid4)
    constraint_type: ConstraintType
    subject_ids: list[UUID] = Field(default_factory=list)
    strength: ConstraintStrength = ConstraintStrength.PREFERRED
    params: dict = Field(default_factory=dict)
    confidence: float = 1.0
    source: str = ""
    is_satisfied: bool = True
    violation_amount: float = 0.0


class ConstraintGraph(BaseModel):
    constraint_graph_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    constraints: list[Constraint] = Field(default_factory=list)
    violation_count: int = 0
    unresolved_count: int = 0


# ═══════════════════════════════════════════════════════════
# Repair
# ═══════════════════════════════════════════════════════════

class RepairAction(BaseModel):
    repair_id: UUID = Field(default_factory=uuid4)
    object_refs: list[UUID] = Field(default_factory=list)
    reason: str = ""
    rule: str = ""
    confidence: float = 1.0
    original_geometry: Optional[dict] = None  # serialized original
    resulting_geometry: Optional[dict] = None
    is_reversible: bool = True
    is_validated: bool = False
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    reversed: bool = False

    def reverse(self) -> "RepairAction":
        """Create reverse action by swapping original/resulting."""
        return RepairAction(
            object_refs=self.object_refs.copy(),
            reason=f"REVERSED: {self.reason}",
            rule=self.rule,
            confidence=self.confidence,
            original_geometry=self.resulting_geometry,
            resulting_geometry=self.original_geometry,
            is_reversible=False,
        )


class RepairLog(BaseModel):
    repair_log_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    actions: list[RepairAction] = Field(default_factory=list)
    total_repairs: int = 0
    accepted: int = 0
    rejected: int = 0


class AmbiguityItem(BaseModel):
    ambiguity_id: UUID = Field(default_factory=uuid4)
    object_ref: UUID
    object_type: str
    region: BoundingBox2D
    description: str
    candidates: list[str] = Field(default_factory=list)
    severity: Literal["critical", "major", "minor"] = "major"
    requires_review: bool = True
    resolved: bool = False
    resolution: Optional[str] = None


class AmbiguityReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    items: list[AmbiguityItem] = Field(default_factory=list)
    total: int = 0
    critical: int = 0
    unresolved: int = 0


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class ValidationSeverity(str, Enum):
    BLOCKING = "blocking"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationDecision(BaseModel):
    validator_id: str
    validator_version: str = "3.0.0"
    object_ref: UUID
    object_type: str
    decision: Literal["pass", "fail", "warn"]
    severity: ValidationSeverity = ValidationSeverity.WARNING
    issue_code: Optional[str] = None
    description: str = ""
    measured_deviation: float = 0.0
    evidence: dict = Field(default_factory=dict)
    suggested_correction: Optional[str] = None


class ValidationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    decisions: list[ValidationDecision] = Field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    warn_count: int = 0
    blocking_count: int = 0
    is_clean: bool = False
    can_complete: bool = False


# ═══════════════════════════════════════════════════════════
# Quality Metrics
# ═══════════════════════════════════════════════════════════

class GeometryMetrics(BaseModel):
    metrics_id: UUID = Field(default_factory=uuid4)
    floor_id: Optional[UUID] = None
    wall_detection_retention: float = 0.0
    wall_connectivity_rate: float = 0.0
    endpoint_gap_rate: float = 0.0
    intersection_accuracy: float = 0.0
    room_closure_rate: float = 0.0
    room_overlap_rate: float = 0.0
    opening_host_accuracy: float = 0.0
    scale_deviation_pct: float = 0.0
    area_consistency: float = 0.0
    topology_completeness: float = 0.0
    constraint_violation_count: int = 0
    unresolved_ambiguity_count: int = 0
    repair_acceptance_rate: float = 1.0
    user_correction_rate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Edit Operations
# ═══════════════════════════════════════════════════════════

class EditType(str, Enum):
    ADD_WALL = "add_wall"
    REMOVE_WALL = "remove_wall"
    MOVE_WALL = "move_wall"
    MOVE_ENDPOINT = "move_endpoint"
    JOIN_WALLS = "join_walls"
    SPLIT_WALL = "split_wall"
    CHANGE_THICKNESS = "change_thickness"
    ADD_ROOM = "add_room"
    RENAME_ROOM = "rename_room"
    CHANGE_ROOM_BOUNDARY = "change_room_boundary"
    ADD_DOOR = "add_door"
    MOVE_DOOR = "move_door"
    CHANGE_DOOR_WIDTH = "change_door_width"
    ADD_WINDOW = "add_window"
    MOVE_WINDOW = "move_window"
    CHANGE_SCALE = "change_scale"
    RESOLVE_AMBIGUITY = "resolve_ambiguity"
    ACCEPT_REPAIR = "accept_repair"
    REJECT_REPAIR = "reject_repair"


class EditOperation(BaseModel):
    edit_id: UUID = Field(default_factory=uuid4)
    edit_type: EditType
    object_ref: Optional[UUID] = None
    params: dict = Field(default_factory=dict)
    previous_state: Optional[dict] = None  # for undo
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    version_before: int = 0
    version_after: int = 0
    is_undone: bool = False


class EditHistory(BaseModel):
    history_id: UUID = Field(default_factory=uuid4)
    floor_id: UUID
    edits: list[EditOperation] = Field(default_factory=list)
    current_version: int = 1
    undo_stack: list[int] = Field(default_factory=list)  # edit indices
    redo_stack: list[int] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Scale Calibration Result
# ═══════════════════════════════════════════════════════════

class ScaleCalibrationResult(BaseModel):
    calibration_id: UUID = Field(default_factory=uuid4)
    units: str = "mm"
    pixels_per_mm: float = 0.0
    mm_per_pixel: float = 0.0
    scale_ratio: str = "1:1"
    confidence: float = 0.0
    method: str = ""
    source_evidence: list[str] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    calibration_error_pct: float = 0.0
    manual_override: bool = False
    anisotropic: bool = False
    anisotropic_ratio: float = 1.0

    def px_to_mm(self, px: float) -> float:
        return px * self.mm_per_pixel if self.mm_per_pixel > 0 else 0.0

    def mm_to_px(self, mm: float) -> float:
        return mm * self.pixels_per_mm if self.pixels_per_mm > 0 else 0.0


# ═══════════════════════════════════════════════════════════
# Complete Geometry Model
# ═══════════════════════════════════════════════════════════

class GeometryModel(BaseModel):
    """The authoritative Phase 3 output — editable metric floor plan."""
    model_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_graph_id: UUID
    source_graph_version: int = 1
    calibration: Optional[ScaleCalibrationResult] = None
    coordinate_systems: dict[CoordSystem, CoordTransform] = Field(default_factory=dict)
    floors: list[FloorGeometry] = Field(default_factory=list)
    topology: Optional[TopologyGraph] = None
    constraints: Optional[ConstraintGraph] = None
    repair_log: Optional[RepairLog] = None
    ambiguity_report: Optional[AmbiguityReport] = None
    validation: Optional[ValidationReport] = None
    metrics: Optional[GeometryMetrics] = None
    edit_history: Optional[EditHistory] = None
    version: int = 1
    state: GeometryState = GeometryState.PROVISIONAL
    is_complete: bool = False
    completeness_issues: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Pipeline Result
# ═══════════════════════════════════════════════════════════

class GeometryPipelineResult(BaseModel):
    """Complete Phase 3 pipeline output."""
    result_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_graph_id: Optional[UUID] = None
    model: Optional[GeometryModel] = None
    pipeline_version: str = "3.0.0"
    total_duration_ms: float = 0.0
    stages_completed: list[str] = Field(default_factory=list)
    stages_failed: list[str] = Field(default_factory=list)
    checkpoint: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
