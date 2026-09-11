"""
Vision 5D — Phase 3 Geometry Engine
"""
from packages.geometry.contracts import (
    # Coordinate Systems
    CoordSystem, CoordTransform,
    # Primitives
    Point2D, Line2D, Polygon2D, BoundingBox2D,
    # Geometry State
    GeometryState, ConstraintStrength, JunctionType,
    # Wall
    WallCenterline, WallThickness, WallBody, WallJunction,
    # Opening
    Opening, OpeningType, OpeningSwing,
    # Room
    RoomGeometry,
    # Floor
    FloorGeometry,
    # Topology
    TopologyRelation, TopologyEdge, TopologyGraph,
    # Constraints
    ConstraintType, Constraint, ConstraintGraph,
    # Repair
    RepairAction, RepairLog, AmbiguityItem, AmbiguityReport,
    # Validation
    ValidationSeverity, ValidationDecision, ValidationReport,
    # Metrics
    GeometryMetrics,
    # Edit
    EditType, EditOperation, EditHistory,
    # Scale
    ScaleCalibrationResult,
    # Model
    GeometryModel,
    # Pipeline
    GeometryPipelineResult,
)

from packages.geometry.primitives import (
    CoordTransformEngine, wall_reconstructor, wall_body_builder, coord_engine,
)
from packages.geometry.thickness import thickness_estimator
from packages.geometry.rooms import room_engine
from packages.geometry.openings import opening_engine
from packages.geometry.scale import scale_calibrator
from packages.geometry.constraints import constraint_engine, geometric_solver
from packages.geometry.topology import topology_engine
from packages.geometry.repair import geom_repair_engine, uncertainty_handler
from packages.geometry.validation import geometry_validator, metrics_calculator
from packages.geometry.model import editable_model
from packages.geometry.pipeline import geometry_pipeline

__all__ = [
    "CoordSystem", "CoordTransform", "CoordTransformEngine",
    "Point2D", "Line2D", "Polygon2D", "BoundingBox2D",
    "GeometryState", "ConstraintStrength", "JunctionType",
    "WallCenterline", "WallThickness", "WallBody", "WallJunction",
    "Opening", "OpeningType", "OpeningSwing",
    "RoomGeometry", "FloorGeometry",
    "TopologyRelation", "TopologyEdge", "TopologyGraph",
    "ConstraintType", "Constraint", "ConstraintGraph",
    "RepairAction", "RepairLog", "AmbiguityItem", "AmbiguityReport",
    "ValidationSeverity", "ValidationDecision", "ValidationReport",
    "GeometryMetrics",
    "EditType", "EditOperation", "EditHistory",
    "ScaleCalibrationResult", "GeometryModel", "GeometryPipelineResult",
    "wall_reconstructor", "wall_body_builder", "coord_engine",
    "thickness_estimator", "room_engine", "opening_engine",
    "scale_calibrator", "constraint_engine", "geometric_solver",
    "topology_engine", "geom_repair_engine", "uncertainty_handler",
    "geometry_validator", "metrics_calculator",
    "editable_model", "geometry_pipeline",
]
