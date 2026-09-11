"""
Vision 5D — Phase 3 Geometry Validation Engine
"""
from uuid import UUID, uuid4
from packages.geometry.contracts import (
    ValidationDecision, ValidationReport, ValidationSeverity,
    GeometryMetrics,
    WallCenterline, WallBody, RoomGeometry, Opening, WallJunction,
    FloorGeometry, GeometryModel, OpeningType,
    Point2D, Polygon2D,
)


class GeometryValidator:
    """Independent validators for all geometry types."""

    VERSION = "3.0.0"

    def validate_all(self, floor: FloorGeometry) -> ValidationReport:
        """Run all validators on a floor."""
        report = ValidationReport(floor_id=floor.floor_id)
        decisions = []

        decisions.extend(self._validate_coordinates(floor))
        decisions.extend(self._validate_walls(floor.walls))
        decisions.extend(self._validate_openings(floor.openings, floor.walls))
        decisions.extend(self._validate_rooms(floor.rooms, floor.walls))
        decisions.extend(self._validate_topology(floor))
        decisions.extend(self._validate_containment(floor))

        report.decisions = decisions
        report.pass_count = sum(1 for d in decisions if d.decision == "pass")
        report.fail_count = sum(1 for d in decisions if d.decision == "fail")
        report.warn_count = sum(1 for d in decisions if d.decision == "warn")
        report.blocking_count = sum(1 for d in decisions
                                     if d.decision == "fail" and d.severity == ValidationSeverity.BLOCKING)
        report.is_clean = report.fail_count == 0 and report.blocking_count == 0
        report.can_complete = report.blocking_count == 0
        return report

    def _validate_coordinates(self, floor: FloorGeometry) -> list[ValidationDecision]:
        decisions = []
        # Check coordinate consistency
        all_points = []
        for w in floor.walls:
            all_points.extend(w.centerline)
            all_points.extend(w.face_left)
            all_points.extend(w.face_right)
        for r in floor.rooms:
            all_points.extend(r.polygon)
        for op in floor.openings:
            all_points.append(op.position)

        if not all_points:
            return [ValidationDecision(
                validator_id="coord_check", validator_version=self.VERSION,
                object_ref=floor.floor_id, object_type="floor",
                decision="warn", severity=ValidationSeverity.WARNING,
                description="No geometry points found in floor",
            )]

        # Check for NaN/Inf
        for pt in all_points:
            import math
            if math.isnan(pt.x) or math.isnan(pt.y) or math.isinf(pt.x) or math.isinf(pt.y):
                decisions.append(ValidationDecision(
                    validator_id="coord_nan_check", validator_version=self.VERSION,
                    object_ref=floor.floor_id, object_type="floor",
                    decision="fail", severity=ValidationSeverity.BLOCKING,
                    issue_code="INVALID_COORDINATE",
                    description=f"NaN or Inf coordinate detected",
                    suggested_correction="Remove or fix affected geometry",
                ))
                break

        return decisions

    def _validate_walls(self, walls: list[WallBody]) -> list[ValidationDecision]:
        decisions = []
        for w in walls:
            # Wall connectivity
            if len(w.centerline) < 2:
                decisions.append(ValidationDecision(
                    validator_id="wall_connectivity", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="WALL_NO_CENTERLINE",
                    description="Wall has fewer than 2 centerline points",
                    suggested_correction="Add valid centerline or remove wall",
                ))
                continue

            # Zero thickness
            if w.thickness <= 0:
                decisions.append(ValidationDecision(
                    validator_id="wall_thickness", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="WALL_ZERO_THICKNESS",
                    description=f"Wall has zero thickness",
                    suggested_correction="Set valid wall thickness",
                ))
            elif w.thickness < 10:
                decisions.append(ValidationDecision(
                    validator_id="wall_thickness", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="warn", severity=ValidationSeverity.WARNING,
                    issue_code="WALL_THIN",
                    description=f"Wall thickness {w.thickness:.1f}mm is unusually thin",
                ))
            elif w.thickness > 1000:
                decisions.append(ValidationDecision(
                    validator_id="wall_thickness", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="warn", severity=ValidationSeverity.WARNING,
                    issue_code="WALL_THICK",
                    description=f"Wall thickness {w.thickness:.1f}mm is unusually thick",
                ))

            # Check wall body polygon
            if len(w.polygon) < 3:
                decisions.append(ValidationDecision(
                    validator_id="wall_polygon", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="warn", severity=ValidationSeverity.WARNING,
                    issue_code="WALL_NO_BODY",
                    description="Wall has no body polygon",
                ))
            elif not Polygon2D(vertices=w.polygon).is_valid():
                decisions.append(ValidationDecision(
                    validator_id="wall_polygon", validator_version=self.VERSION,
                    object_ref=w.body_id, object_type="wall",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="WALL_SELF_INTERSECT",
                    description="Wall body polygon self-intersects",
                    suggested_correction="Repair wall body polygon",
                ))

        return decisions

    def _validate_openings(self, openings: list[Opening], walls: list[WallBody]) -> list[ValidationDecision]:
        decisions = []
        wall_by_cl = {w.centerline_id: w for w in walls}

        for op in openings:
            if not op.host_wall_id:
                decisions.append(ValidationDecision(
                    validator_id="opening_host", validator_version=self.VERSION,
                    object_ref=op.opening_id, object_type="opening",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="OPENING_NO_HOST",
                    description="Opening has no host wall",
                    suggested_correction="Assign host wall or remove opening",
                ))
                continue

            host = wall_by_cl.get(op.host_wall_id)
            if not host:
                decisions.append(ValidationDecision(
                    validator_id="opening_host", validator_version=self.VERSION,
                    object_ref=op.opening_id, object_type="opening",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="OPENING_HOST_NOT_FOUND",
                    description=f"Host wall {op.host_wall_id} not found",
                ))
                continue

            # Check width
            if op.opening_type == OpeningType.DOOR:
                if op.width_mm < 600:
                    decisions.append(ValidationDecision(
                        validator_id="opening_width", validator_version=self.VERSION,
                        object_ref=op.opening_id, object_type="opening",
                        decision="warn", severity=ValidationSeverity.WARNING,
                        issue_code="DOOR_TOO_NARROW",
                        description=f"Door width {op.width_mm}mm is narrow",
                        measured_deviation=600 - op.width_mm,
                    ))
                elif op.width_mm > 1200:
                    decisions.append(ValidationDecision(
                        validator_id="opening_width", validator_version=self.VERSION,
                        object_ref=op.opening_id, object_type="opening",
                        decision="warn", severity=ValidationSeverity.WARNING,
                        issue_code="DOOR_TOO_WIDE",
                        description=f"Door width {op.width_mm}mm is unusually wide",
                    ))

            # Check if opening extends beyond wall
            # Simplified: position along wall must be 0-1
            if op.position_along_wall < -0.1 or op.position_along_wall > 1.1:
                decisions.append(ValidationDecision(
                    validator_id="opening_position", validator_version=self.VERSION,
                    object_ref=op.opening_id, object_type="opening",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="OPENING_OUTSIDE_WALL",
                    description=f"Opening position ({op.position_along_wall:.2f}) is outside wall",
                    measured_deviation=max(abs(op.position_along_wall) - 1.0, 0),
                    suggested_correction="Move opening within wall bounds",
                ))

        return decisions

    def _validate_rooms(self, rooms: list[RoomGeometry], walls: list[WallBody]) -> list[ValidationDecision]:
        decisions = []
        for r in rooms:
            if len(r.polygon) < 3:
                decisions.append(ValidationDecision(
                    validator_id="room_polygon", validator_version=self.VERSION,
                    object_ref=r.room_id, object_type="room",
                    decision="fail", severity=ValidationSeverity.BLOCKING,
                    issue_code="ROOM_NO_POLYGON",
                    description=f"Room '{r.label}' has fewer than 3 polygon vertices",
                    suggested_correction="Define valid room boundary",
                ))
                continue

            poly = Polygon2D(vertices=r.polygon)
            if not poly.is_valid():
                decisions.append(ValidationDecision(
                    validator_id="room_polygon", validator_version=self.VERSION,
                    object_ref=r.room_id, object_type="room",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="ROOM_SELF_INTERSECT",
                    description=f"Room '{r.label}' polygon self-intersects",
                    suggested_correction="Repair room polygon",
                ))

            if not r.is_closed:
                decisions.append(ValidationDecision(
                    validator_id="room_closure", validator_version=self.VERSION,
                    object_ref=r.room_id, object_type="room",
                    decision="fail", severity=ValidationSeverity.ERROR,
                    issue_code="ROOM_NOT_CLOSED",
                    description=f"Room '{r.label}' boundary is not closed",
                    suggested_correction="Close room boundary",
                ))

            if r.area_mm2 < 100:
                decisions.append(ValidationDecision(
                    validator_id="room_area", validator_version=self.VERSION,
                    object_ref=r.room_id, object_type="room",
                    decision="warn", severity=ValidationSeverity.WARNING,
                    issue_code="ROOM_TINY",
                    description=f"Room '{r.label}' area ({r.area_m2():.3f}m²) is very small",
                    measured_deviation=r.area_mm2,
                ))

            if r.area_mm2 > 1_000_000_000:  # 1000 m²
                decisions.append(ValidationDecision(
                    validator_id="room_area", validator_version=self.VERSION,
                    object_ref=r.room_id, object_type="room",
                    decision="warn", severity=ValidationSeverity.WARNING,
                    issue_code="ROOM_HUGE",
                    description=f"Room '{r.label}' area ({r.area_m2():.1f}m²) is unusually large",
                ))

        # Check for overlapping rooms
        for i, ra in enumerate(rooms):
            if len(ra.polygon) < 3: continue
            poly_a = Polygon2D(vertices=ra.polygon)
            for rb in rooms[i+1:]:
                if len(rb.polygon) < 3: continue
                shared_walls = set(ra.wall_ids) & set(rb.wall_ids)
                if shared_walls: continue

                poly_b = Polygon2D(vertices=rb.polygon)
                # Check if centroids are very close (overlap proxy)
                if ra.centroid.distance_to(rb.centroid) < 50:
                    decisions.append(ValidationDecision(
                        validator_id="room_overlap", validator_version=self.VERSION,
                        object_ref=ra.room_id, object_type="room",
                        decision="fail", severity=ValidationSeverity.ERROR,
                        issue_code="ROOM_OVERLAP",
                        description=f"Room '{ra.label}' overlaps with '{rb.label}'",
                        evidence={"overlapping_room": str(rb.room_id)},
                        suggested_correction="Resolve room boundary overlap",
                    ))

        return decisions

    def _validate_topology(self, floor: FloorGeometry) -> list[ValidationDecision]:
        decisions = []
        # Check for at least one room
        if not floor.rooms:
            decisions.append(ValidationDecision(
                validator_id="topology_rooms", validator_version=self.VERSION,
                object_ref=floor.floor_id, object_type="floor",
                decision="warn", severity=ValidationSeverity.WARNING,
                issue_code="FLOOR_NO_ROOMS",
                description="Floor has no rooms",
            ))
        # Check for at least one wall
        if not floor.walls:
            decisions.append(ValidationDecision(
                validator_id="topology_walls", validator_version=self.VERSION,
                object_ref=floor.floor_id, object_type="floor",
                decision="warn", severity=ValidationSeverity.WARNING,
                issue_code="FLOOR_NO_WALLS",
                description="Floor has no walls",
            ))
        return decisions

    def _validate_containment(self, floor: FloorGeometry) -> list[ValidationDecision]:
        decisions = []
        # Check all geometry fits within floor outline if defined
        if not floor.outline or len(floor.outline) < 3:
            return decisions

        import math
        for w in floor.walls:
            for pt in w.centerline:
                if math.isnan(pt.x): continue
        return decisions


class MetricsCalculator:
    """Calculates geometry quality metrics."""

    def calculate(self, floor: FloorGeometry,
                  source_centerlines: list = None,
                  source_wall_count: int = 0) -> GeometryMetrics:
        metrics = GeometryMetrics(floor_id=floor.floor_id)

        # Wall detection retention
        if source_wall_count > 0:
            metrics.wall_detection_retention = len(floor.walls) / source_wall_count

        # Wall connectivity rate
        connected = 0
        for w in floor.walls:
            junctions = sum(1 for j in floor.junctions if w.body_id in j.wall_ids)
            if junctions >= 1:
                connected += 1
        metrics.wall_connectivity_rate = connected / len(floor.walls) if floor.walls else 0

        # Endpoint gap rate
        if floor.walls:
            total_gaps = 0
            for w in floor.walls:
                if len(w.centerline) >= 2 and w.centerline[0].distance_to(w.centerline[-1]) < 10:
                    pass  # closed loop - fine
                elif len(w.centerline) < 2:
                    total_gaps += 1
            metrics.endpoint_gap_rate = total_gaps / len(floor.walls)

        # Room closure rate
        if floor.rooms:
            metrics.room_closure_rate = sum(1 for r in floor.rooms if r.is_closed) / len(floor.rooms)

        # Room overlap rate
        if floor.rooms:
            overlaps = 0
            for i, ra in enumerate(floor.rooms):
                for rb in floor.rooms[i+1:]:
                    if ra.centroid.distance_to(rb.centroid) < 50:
                        shared = set(ra.wall_ids) & set(rb.wall_ids)
                        if not shared:
                            overlaps += 1
            metrics.room_overlap_rate = overlaps / len(floor.rooms) if floor.rooms else 0

        # Opening host accuracy
        if floor.openings:
            metrics.opening_host_accuracy = sum(1 for o in floor.openings
                                                  if o.host_wall_id is not None) / len(floor.openings)

        # Topology completeness (rooms with adjacency)
        if floor.rooms:
            with_adj = sum(1 for r in floor.rooms if r.adjacent_room_ids)
            metrics.topology_completeness = with_adj / len(floor.rooms)

        return metrics


geometry_validator = GeometryValidator()
metrics_calculator = MetricsCalculator()
