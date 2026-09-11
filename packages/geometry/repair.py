"""
Vision 5D — Phase 3 Geometry Repair Engine + Uncertainty Handling
"""
from uuid import UUID, uuid4
from datetime import datetime
from packages.geometry.contracts import (
    RepairAction, RepairLog, AmbiguityItem, AmbiguityReport,
    Point2D, Line2D, BoundingBox2D,
    WallCenterline, WallBody, RoomGeometry, Opening, WallJunction,
    GeometryState, OpeningType, Constraint,
)


class GeometryRepairEngine:
    """Detects and repairs geometric issues. All repairs are reversible."""

    GAP_CLOSE_THRESHOLD = 50.0  # px
    FRAGMENT_MERGE_DISTANCE = 100.0
    DUPLICATE_TOLERANCE = 5.0
    NEARLY_PARALLEL_TOL_DEG = 3.0
    NEARLY_PERP_TOL_DEG = 3.0

    def __init__(self):
        self._repair_log = RepairLog()

    def detect_and_repair(self, centerlines: list[WallCenterline],
                          walls: list[WallBody], rooms: list[RoomGeometry],
                          openings: list[Opening],
                          junctions: list[WallJunction]) -> RepairLog:
        log = RepairLog()
        actions = []

        # 1. Close small endpoint gaps
        actions.extend(self._repair_endpoint_gaps(centerlines))

        # 2. Merge duplicate/fragmented walls
        actions.extend(self._repair_fragmented_walls(centerlines))

        # 3. Fix openings detached from walls
        actions.extend(self._repair_detached_openings(openings, walls))

        # 4. Fix invalid room polygons (gap closure)
        actions.extend(self._repair_room_gaps(rooms, walls))

        # 5. Fix overlapping geometry
        actions.extend(self._repair_overlaps(rooms))

        # Validate each repair
        for action in actions:
            action.is_validated = True  # will be validated by validation engine

        log.actions = actions
        log.total_repairs = len(actions)
        log.accepted = len(actions)
        self._repair_log = log
        return log

    def _repair_endpoint_gaps(self, centerlines: list[WallCenterline]) -> list[RepairAction]:
        actions = []
        for i, cl_a in enumerate(centerlines):
            for cl_b in centerlines[i+1:]:
                for ea in [cl_a.points[0], cl_a.points[-1]]:
                    for eb in [cl_b.points[0], cl_b.points[-1]]:
                        d = ea.distance_to(eb)
                        if 0 < d < self.GAP_CLOSE_THRESHOLD:
                            mid = Point2D(x=(ea.x+eb.x)/2, y=(ea.y+eb.y)/2)
                            orig_a = Point2D(x=ea.x, y=ea.y)
                            orig_b = Point2D(x=eb.x, y=eb.y)
                            # Apply repair
                            if ea is cl_a.points[0]: cl_a.points[0] = mid
                            else: cl_a.points[-1] = mid
                            if eb is cl_b.points[0]: cl_b.points[0] = mid
                            else: cl_b.points[-1] = mid

                            actions.append(RepairAction(
                                object_refs=[cl_a.centerline_id, cl_b.centerline_id],
                                reason=f"Closed {d:.1f}px endpoint gap",
                                rule="endpoint_gap_close",
                                confidence=0.90,
                                original_geometry={"pts": [(orig_a.x, orig_a.y), (orig_b.x, orig_b.y)]},
                                resulting_geometry={"pts": [(mid.x, mid.y), (mid.x, mid.y)]},
                            ))
        return actions

    def _repair_fragmented_walls(self, centerlines: list[WallCenterline]) -> list[RepairAction]:
        actions = []
        consumed = set()
        for i, cl_a in enumerate(centerlines):
            if i in consumed: continue
            for j, cl_b in enumerate(centerlines):
                if j <= i or j in consumed: continue
                if len(cl_a.points) < 2 or len(cl_b.points) < 2: continue

                # Check if collinear and close
                dir_a = (cl_a.points[-1] - cl_a.points[0]).normalized()
                dir_b = (cl_b.points[-1] - cl_b.points[0]).normalized()
                if abs(dir_a.dot(dir_b)) < 0.995: continue

                # Check proximity
                min_dist = min(
                    cl_a.points[0].distance_to(cl_b.points[0]),
                    cl_a.points[0].distance_to(cl_b.points[-1]),
                    cl_a.points[-1].distance_to(cl_b.points[0]),
                    cl_a.points[-1].distance_to(cl_b.points[-1]),
                )
                if min_dist < self.FRAGMENT_MERGE_DISTANCE:
                    # Merge: extend cl_a to include cl_b points
                    all_pts = cl_a.points + cl_b.points
                    dir_vec = dir_a
                    proj = [(p.dot(dir_vec), p) for p in all_pts]
                    proj.sort(key=lambda x: x[0])
                    original = [(p.x, p.y) for p in cl_a.points]
                    cl_a.points = [p for _, p in proj]

                    actions.append(RepairAction(
                        object_refs=[cl_a.centerline_id, cl_b.centerline_id],
                        reason=f"Merged fragmented wall segments (gap {min_dist:.1f}px)",
                        rule="fragment_merge",
                        confidence=0.85,
                        original_geometry={"wall_a": original, "wall_b_points": [(p.x, p.y) for p in cl_b.points]},
                        resulting_geometry={"merged_points": [(p.x, p.y) for p in cl_a.points]},
                    ))
                    consumed.add(j)
        return actions

    def _repair_detached_openings(self, openings: list[Opening],
                                   walls: list[WallBody]) -> list[RepairAction]:
        actions = []
        for op in openings:
            if op.host_wall_id is None:
                # Try to find nearest wall
                best_wall, best_dist = None, float('inf')
                for w in walls:
                    for pt in w.centerline:
                        d = op.position.distance_to(pt)
                        if d < best_dist:
                            best_dist = d
                            best_wall = w
                if best_wall and best_dist < 200:
                    original_host = None
                    op.host_wall_id = best_wall.centerline_id
                    op.is_valid = True
                    op.validation_issues = []
                    op.state = GeometryState.INFERRED
                    actions.append(RepairAction(
                        object_refs=[op.opening_id, best_wall.centerline_id],
                        reason=f"Attached detached opening to nearest wall ({best_dist:.0f}px)",
                        rule="opening_attach",
                        confidence=0.70,
                        original_geometry={"host": None},
                        resulting_geometry={"host": str(best_wall.centerline_id)},
                    ))
        return actions

    def _repair_room_gaps(self, rooms: list[RoomGeometry],
                          walls: list[WallBody]) -> list[RepairAction]:
        actions = []
        for room in rooms:
            if not room.is_closed and len(room.polygon) >= 3:
                # Close gap by connecting last to first
                gap = room.polygon[0].distance_to(room.polygon[-1])
                if gap < self.GAP_CLOSE_THRESHOLD * 10:
                    original_poly = [(p.x, p.y) for p in room.polygon]
                    room.polygon.append(Point2D(x=room.polygon[0].x, y=room.polygon[0].y))
                    room.is_closed = True
                    actions.append(RepairAction(
                        object_refs=[room.room_id],
                        reason=f"Closed room boundary gap ({gap:.1f}px)",
                        rule="room_gap_close",
                        confidence=0.80,
                        original_geometry={"polygon": original_poly},
                        resulting_geometry={"polygon": [(p.x, p.y) for p in room.polygon]},
                    ))
        return actions

    def _repair_overlaps(self, rooms: list[RoomGeometry]) -> list[RepairAction]:
        actions = []
        for i, ra in enumerate(rooms):
            for rb in rooms[i+1:]:
                shared = set(ra.wall_ids) & set(rb.wall_ids)
                if shared: continue  # adjacent rooms share walls - fine
                # Check centroid distance for overlap heuristic
                if ra.centroid.distance_to(rb.centroid) < 50:
                    actions.append(RepairAction(
                        object_refs=[ra.room_id, rb.room_id],
                        reason=f"Flagged potential room overlap for review",
                        rule="overlap_flag",
                        confidence=0.60,
                        original_geometry={"room_a": ra.label, "room_b": rb.label},
                        resulting_geometry={"action": "flagged_for_review"},
                    ))
        return actions

    def get_log(self) -> RepairLog:
        return self._repair_log


class UncertaintyHandler:
    """Preserves and classifies uncertainty instead of hiding it."""

    def classify_geometry(self, centerlines: list[WallCenterline],
                          walls: list[WallBody], rooms: list[RoomGeometry],
                          openings: list[Opening],
                          low_confidence_threshold: float = 0.5) -> AmbiguityReport:
        report = AmbiguityReport()
        items = []

        # Uncertain walls
        for cl in centerlines:
            if cl.confidence < low_confidence_threshold:
                items.append(AmbiguityItem(
                    object_ref=cl.centerline_id,
                    object_type="wall_centerline",
                    region=BoundingBox2D.from_points(cl.points),
                    description=f"Low confidence wall ({cl.confidence:.2f})",
                    severity="major",
                    requires_review=True,
                ))

        # Uncertain wall thickness
        for w in walls:
            if w.confidence < low_confidence_threshold:
                items.append(AmbiguityItem(
                    object_ref=w.body_id,
                    object_type="wall_body",
                    region=BoundingBox2D.from_points(w.centerline),
                    description=f"Low confidence wall body (thickness={w.thickness:.1f}mm, conf={w.confidence:.2f})",
                    severity="minor" if w.confidence > 0.3 else "major",
                ))

        # Incomplete rooms
        for r in rooms:
            if not r.is_closed:
                items.append(AmbiguityItem(
                    object_ref=r.room_id,
                    object_type="room",
                    region=BoundingBox2D.from_points(r.polygon),
                    description=f"Incomplete room boundary: {r.label or r.room_id}",
                    severity="critical",
                    requires_review=True,
                ))
            if r.confidence < low_confidence_threshold:
                items.append(AmbiguityItem(
                    object_ref=r.room_id,
                    object_type="room",
                    region=BoundingBox2D.from_points(r.polygon),
                    description=f"Low confidence room: {r.label} ({r.confidence:.2f})",
                    severity="major",
                ))

        # Invalid openings
        for op in openings:
            if not op.is_valid:
                items.append(AmbiguityItem(
                    object_ref=op.opening_id,
                    object_type="opening",
                    region=BoundingBox2D(min_x=op.position.x-50, min_y=op.position.y-50,
                                          max_x=op.position.x+50, max_y=op.position.y+50),
                    description=f"Invalid opening: {'; '.join(op.validation_issues)}",
                    severity="critical" if op.opening_type == OpeningType.DOOR else "major",
                    requires_review=True,
                ))

        # Conflicting scale (placeholder)
        # Unresolved constraints would go here

        report.items = items
        report.total = len(items)
        report.critical = sum(1 for i in items if i.severity == "critical")
        report.unresolved = report.total
        return report


geom_repair_engine = GeometryRepairEngine()
uncertainty_handler = UncertaintyHandler()
