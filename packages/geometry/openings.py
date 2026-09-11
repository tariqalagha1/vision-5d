"""
Vision 5D — Phase 3 Opening Placement Engine
"""
from uuid import UUID, uuid4
from packages.geometry.contracts import (
    Point2D, Line2D,
    Opening, OpeningType, OpeningSwing,
    WallCenterline, WallBody, RoomGeometry,
    GeometryState,
)


class OpeningPlacementEngine:
    """Places doors and windows in host walls with geometric validation."""

    MIN_DOOR_WIDTH = 600
    MAX_DOOR_WIDTH = 1200
    MIN_WINDOW_WIDTH = 400
    MAX_WINDOW_WIDTH = 3000
    DEFAULT_DOOR_WIDTH = 900
    DEFAULT_WINDOW_WIDTH = 1200

    def place_all(self, opening_graph_nodes: list[dict],
                  centerlines: list[WallCenterline],
                  walls: list[WallBody]) -> list[Opening]:
        openings = []
        walls_by_cl = {w.centerline_id: w for w in walls}

        for node in opening_graph_nodes:
            props = node.get("properties", {})
            cls = props.get("class", "door")
            opening_type = OpeningType.DOOR if cls == "door" else OpeningType.WINDOW

            bbox = props.get("bbox", [0, 0, 0, 0])
            pos = Point2D(x=bbox[0] + bbox[2]/2 if len(bbox)>=3 else 0,
                          y=bbox[1] + bbox[3]/2 if len(bbox)>=4 else 0)

            host_cl = self._find_host_wall(pos, centerlines)
            if host_cl is None:
                op = Opening(
                    opening_id=uuid4(),
                    opening_type=opening_type,
                    position=pos,
                    width_mm=self.DEFAULT_DOOR_WIDTH if opening_type == OpeningType.DOOR else self.DEFAULT_WINDOW_WIDTH,
                    graph_node_ref=UUID(node.get("node_id", str(uuid4()))),
                    detection_ref=UUID(node.get("detection_ref", str(uuid4()))) if node.get("detection_ref") else None,
                    confidence=node.get("confidence", 0.7),
                    state=GeometryState.AMBIGUOUS,
                    is_valid=False,
                    validation_issues=["No host wall found"],
                )
            else:
                pos_along = self._position_along_wall(pos, host_cl)
                import math as _m
                dir_vec = host_cl.points[-1] - host_cl.points[0]
                orientation = _m.degrees(_m.atan2(dir_vec.y, dir_vec.x))

                width = self.DEFAULT_DOOR_WIDTH if opening_type == OpeningType.DOOR else self.DEFAULT_WINDOW_WIDTH
                sill = 900 if opening_type == OpeningType.WINDOW else 0.0

                wall_body = walls_by_cl.get(host_cl.centerline_id)
                valid = True
                issues = []

                if wall_body and host_cl.length() > 0:
                    wall_len = host_cl.length()
                    half_w = width / 2
                    pos_mm = pos_along * wall_len
                    if pos_mm - half_w < 0 or pos_mm + half_w > wall_len:
                        valid = False
                        issues.append(f"Opening extends beyond wall (pos={pos_mm:.0f}mm, width={width}mm, wall_len={wall_len:.0f}mm)")

                op = Opening(
                    opening_id=uuid4(),
                    opening_type=opening_type,
                    host_wall_id=host_cl.centerline_id,
                    position_along_wall=pos_along,
                    position=pos,
                    width_mm=width,
                    height_mm=2100.0 if opening_type == OpeningType.DOOR else 1200.0,
                    orientation_deg=orientation,
                    swing=OpeningSwing.INWARD if opening_type == OpeningType.DOOR else OpeningSwing.UNKNOWN,
                    sill_height_mm=sill,
                    graph_node_ref=UUID(node.get("node_id", str(uuid4()))),
                    detection_ref=UUID(node.get("detection_ref", str(uuid4()))) if node.get("detection_ref") else None,
                    confidence=node.get("confidence", 0.7),
                    state=GeometryState.INFERRED if valid else GeometryState.AMBIGUOUS,
                    is_valid=valid,
                    validation_issues=issues,
                )
            openings.append(op)

        return openings

    def _find_host_wall(self, pos: Point2D, centerlines: list[WallCenterline]) -> WallCenterline | None:
        best, best_dist = None, float('inf')
        for cl in centerlines:
            for line in cl.as_lines():
                d = line.distance_to_point(pos)
                if d < best_dist:
                    best_dist = d
                    best = cl
        return best if best_dist < 500 else None

    @staticmethod
    def _position_along_wall(pos: Point2D, cl: WallCenterline) -> float:
        if len(cl.points) < 2: return 0.5
        total_len = cl.length()
        if total_len < 1: return 0.5
        p0 = cl.points[0]
        dir_vec = (cl.points[-1] - cl.points[0]).normalized()
        proj = (pos - p0).dot(dir_vec)
        return max(0.0, min(1.0, proj / total_len))

    def validate(self, opening: Opening, wall: WallBody = None) -> Opening:
        opening.validation_issues = []
        opening.is_valid = True
        if not opening.host_wall_id:
            opening.is_valid = False
            opening.validation_issues.append("No host wall assigned")
            return opening
        if opening.opening_type == OpeningType.DOOR:
            if not (self.MIN_DOOR_WIDTH <= opening.width_mm <= self.MAX_DOOR_WIDTH):
                opening.is_valid = False
                opening.validation_issues.append(
                    f"Door width {opening.width_mm}mm outside range [{self.MIN_DOOR_WIDTH}, {self.MAX_DOOR_WIDTH}]")
        elif opening.opening_type == OpeningType.WINDOW:
            if not (self.MIN_WINDOW_WIDTH <= opening.width_mm <= self.MAX_WINDOW_WIDTH):
                opening.is_valid = False
                opening.validation_issues.append(
                    f"Window width {opening.width_mm}mm outside range [{self.MIN_WINDOW_WIDTH}, {self.MAX_WINDOW_WIDTH}]")
        return opening


opening_engine = OpeningPlacementEngine()
