"""
Vision 5D — Phase 3 Constraint Engine + Geometric Solver
"""
from uuid import UUID, uuid4
import math
from packages.geometry.contracts import (
    Constraint, ConstraintType, ConstraintStrength, ConstraintGraph,
    Point2D, Line2D, WallCenterline, WallBody, RoomGeometry, Opening,
    GeometryState,
)


class ConstraintEngine:
    """Creates and manages geometric constraints."""

    PARALLEL_TOL_DEG = 3.0
    PERP_TOL_DEG = 3.0
    HORIZONTAL_TOL_DEG = 2.0
    VERTICAL_TOL_DEG = 2.0

    def build_constraints(self, centerlines: list[WallCenterline],
                          walls: list[WallBody], rooms: list[RoomGeometry],
                          openings: list[Opening],
                          dimension_refs: list[dict] = None) -> ConstraintGraph:
        graph = ConstraintGraph()
        constraints = []

        # Wall constraints
        for cl in centerlines:
            if len(cl.points) < 2: continue
            angle = (cl.points[-1] - cl.points[0]).angle_deg()
            angle = angle % 360

            # Horizontal/vertical detection
            if abs(angle) < self.HORIZONTAL_TOL_DEG or abs(angle - 180) < self.HORIZONTAL_TOL_DEG:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.HORIZONTAL,
                    subject_ids=[cl.centerline_id],
                    strength=ConstraintStrength.PREFERRED,
                    confidence=0.80,
                    source="angle_detection",
                ))
            elif abs(angle - 90) < self.VERTICAL_TOL_DEG or abs(angle - 270) < self.VERTICAL_TOL_DEG:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.VERTICAL,
                    subject_ids=[cl.centerline_id],
                    strength=ConstraintStrength.PREFERRED,
                    confidence=0.80,
                    source="angle_detection",
                ))

        # Pairwise wall constraints
        for i, cl_a in enumerate(centerlines):
            if len(cl_a.points) < 2: continue
            for cl_b in centerlines[i+1:]:
                if len(cl_b.points) < 2: continue
                angle_a = (cl_a.points[-1] - cl_a.points[0]).angle_deg() % 180
                angle_b = (cl_b.points[-1] - cl_b.points[0]).angle_deg() % 180
                diff = abs(angle_a - angle_b) % 180
                diff = min(diff, 180 - diff)

                if diff < self.PARALLEL_TOL_DEG:
                    constraints.append(Constraint(
                        constraint_type=ConstraintType.PARALLEL,
                        subject_ids=[cl_a.centerline_id, cl_b.centerline_id],
                        strength=ConstraintStrength.PREFERRED,
                        confidence=0.75,
                        source="pairwise_parallel",
                    ))
                elif abs(diff - 90) < self.PERP_TOL_DEG:
                    constraints.append(Constraint(
                        constraint_type=ConstraintType.PERPENDICULAR,
                        subject_ids=[cl_a.centerline_id, cl_b.centerline_id],
                        strength=ConstraintStrength.PREFERRED,
                        confidence=0.75,
                        source="pairwise_perpendicular",
                    ))

        # Shared endpoint constraints
        endpoint_map: dict[tuple[int,int], list[UUID]] = {}
        tol = 50  # snap tolerance in px
        for cl in centerlines:
            for pt in [cl.points[0], cl.points[-1]]:
                key = (int(pt.x/tol), int(pt.y/tol))
                if key not in endpoint_map: endpoint_map[key] = []
                endpoint_map[key].append(cl.centerline_id)

        for key, wall_ids in endpoint_map.items():
            if len(wall_ids) >= 2:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.SHARED_ENDPOINT,
                    subject_ids=list(set(wall_ids)),
                    strength=ConstraintStrength.STRONG,
                    confidence=0.90,
                    source="shared_endpoint",
                ))

        # Opening attachment constraints
        for op in openings:
            if op.host_wall_id:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.ATTACHED_OPENING,
                    subject_ids=[op.opening_id, op.host_wall_id],
                    strength=ConstraintStrength.REQUIRED,
                    confidence=op.confidence,
                    source="opening_attachment",
                ))

        # Room closure constraints
        for room in rooms:
            if room.is_closed:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.CLOSED_POLYGON,
                    subject_ids=[room.room_id] + [w for w in room.wall_ids],
                    strength=ConstraintStrength.REQUIRED,
                    confidence=0.85,
                    source="room_closure",
                ))

        # Non-overlap between rooms
        for i, ra in enumerate(rooms):
            for rb in rooms[i+1:]:
                constraints.append(Constraint(
                    constraint_type=ConstraintType.NON_OVERLAP,
                    subject_ids=[ra.room_id, rb.room_id],
                    strength=ConstraintStrength.STRONG,
                    confidence=0.70,
                    source="room_non_overlap",
                ))

        graph.constraints = constraints
        graph.violation_count = sum(1 for c in constraints if not c.is_satisfied)
        graph.unresolved_count = graph.violation_count
        return graph


class GeometricSolver:
    """Deterministic geometric solver for constraint resolution."""

    SNAP_TOLERANCE = 5.0  # mm
    ALIGNMENT_TOLERANCE = 0.5  # degrees

    def solve(self, centerlines: list[WallCenterline], constraints: list[Constraint],
              repair_log: list = None) -> tuple[list[WallCenterline], list[dict]]:
        """
        Apply constraint resolution and return modified centerlines + repair actions.
        Priority: user corrections > verified dimensions > strong evidence > patterns > weak
        """
        repairs = []
        modified = [WallCenterline(**cl.model_dump()) for cl in centerlines]

        # Sort constraints by strength
        strength_order = {
            ConstraintStrength.REQUIRED: 0,
            ConstraintStrength.STRONG: 1,
            ConstraintStrength.PREFERRED: 2,
            ConstraintStrength.WEAK: 3,
            ConstraintStrength.ADVISORY: 4,
        }
        sorted_constraints = sorted(constraints, key=lambda c: strength_order.get(c.strength, 5))

        for constraint in sorted_constraints:
            if constraint.constraint_type == ConstraintType.SHARED_ENDPOINT:
                self._resolve_shared_endpoint(modified, constraint, repairs)
            elif constraint.constraint_type == ConstraintType.HORIZONTAL:
                self._resolve_horizontal(modified, constraint, repairs)
            elif constraint.constraint_type == ConstraintType.VERTICAL:
                self._resolve_vertical(modified, constraint, repairs)
            elif constraint.constraint_type == ConstraintType.PARALLEL:
                self._resolve_parallel(modified, constraint, repairs)

        return modified, repairs

    def _resolve_shared_endpoint(self, centerlines: list[WallCenterline],
                                  constraint: Constraint, repairs: list[dict]):
        """Snap endpoints of shared-endpoint walls to their centroid."""
        cls = [cl for cl in centerlines if cl.centerline_id in constraint.subject_ids]
        if len(cls) < 2: return

        endpoints = []
        for cl in cls:
            for pt in [cl.points[0], cl.points[-1]]:
                for other in cls:
                    if other.centerline_id == cl.centerline_id: continue
                    for opt in [other.points[0], other.points[-1]]:
                        if pt.distance_to(opt) < self.SNAP_TOLERANCE * 20:
                            endpoints.append((cl, pt))
                            break

        if len(endpoints) < 2: return
        avg = Point2D(
            x=sum(e[1].x for e in endpoints) / len(endpoints),
            y=sum(e[1].y for e in endpoints) / len(endpoints),
        )

        for cl, pt in endpoints:
            if pt is cl.points[0]:
                cl.points[0] = avg
            else:
                cl.points[-1] = avg

        repairs.append({
            "reason": "Snapped shared endpoints to centroid",
            "rule": "shared_endpoint_snap",
            "affected_ids": [cl.centerline_id for cl in cls],
        })

    def _resolve_horizontal(self, centerlines: list[WallCenterline],
                            constraint: Constraint, repairs: list[dict]):
        for cl in centerlines:
            if cl.centerline_id not in constraint.subject_ids: continue
            if len(cl.points) < 2: continue
            avg_y = (cl.points[0].y + cl.points[-1].y) / 2
            cl.points[0] = Point2D(x=cl.points[0].x, y=avg_y)
            cl.points[-1] = Point2D(x=cl.points[-1].x, y=avg_y)
        repairs.append({"reason": "Aligned walls to horizontal", "rule": "horizontal_snap",
                       "affected_ids": constraint.subject_ids})

    def _resolve_vertical(self, centerlines: list[WallCenterline],
                          constraint: Constraint, repairs: list[dict]):
        for cl in centerlines:
            if cl.centerline_id not in constraint.subject_ids: continue
            if len(cl.points) < 2: continue
            avg_x = (cl.points[0].x + cl.points[-1].x) / 2
            cl.points[0] = Point2D(x=avg_x, y=cl.points[0].y)
            cl.points[-1] = Point2D(x=avg_x, y=cl.points[-1].y)
        repairs.append({"reason": "Aligned walls to vertical", "rule": "vertical_snap",
                       "affected_ids": constraint.subject_ids})

    def _resolve_parallel(self, centerlines: list[WallCenterline],
                          constraint: Constraint, repairs: list[dict]):
        """Minor corrections only — preserve original geometry."""
        if len(constraint.subject_ids) < 2: return
        cls = [cl for cl in centerlines if cl.centerline_id in constraint.subject_ids]
        if len(cls) < 2: return
        # Align to the first wall's direction
        ref_dir = (cls[0].points[-1] - cls[0].points[0]).normalized()
        for cl in cls[1:]:
            mid = cl.midpoint()
            l = cl.length()
            new_end = mid + ref_dir * (l / 2)
            new_start = mid - ref_dir * (l / 2)
            cl.points[0] = new_start
            cl.points[-1] = new_end
        repairs.append({"reason": "Aligned walls parallel", "rule": "parallel_align",
                       "affected_ids": constraint.subject_ids})


constraint_engine = ConstraintEngine()
geometric_solver = GeometricSolver()
