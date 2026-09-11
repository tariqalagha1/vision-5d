"""
Vision 5D — Phase 3 Geometric Primitives & Coordinate System Engine
"""
import math
from uuid import UUID
from typing import Optional
from packages.geometry.contracts import (
    Point2D, Line2D, Polygon2D, BoundingBox2D,
    CoordSystem, CoordTransform, WallCenterline, WallBody, WallJunction,
    JunctionType, GeometryState,
)

# ═══════════════════════════════════════════════════════════
# Coordinate Transform Engine
# ═══════════════════════════════════════════════════════════

class CoordTransformEngine:
    """Manages coordinate system transformations."""

    def __init__(self, image_width: int, image_height: int, px_per_mm: float = 0.0):
        self._transforms: dict[tuple[CoordSystem, CoordSystem], CoordTransform] = {}
        self._image_w = max(image_width, 1)
        self._image_h = max(image_height, 1)
        self._px_per_mm = px_per_mm

    def set_scale(self, px_per_mm: float):
        self._px_per_mm = px_per_mm
        self._transforms.clear()

    def get_transform(self, from_sys: CoordSystem, to_sys: CoordSystem) -> CoordTransform:
        key = (from_sys, to_sys)
        if key in self._transforms:
            return self._transforms[key]

        if from_sys == to_sys:
            t = CoordTransform(from_system=from_sys, to_system=to_sys, is_identity=True)
        elif from_sys == CoordSystem.IMAGE and to_sys == CoordSystem.NORMALIZED:
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=1.0/self._image_w, scale_y=1.0/self._image_h,
                              offset_x=0, offset_y=0)
        elif from_sys == CoordSystem.NORMALIZED and to_sys == CoordSystem.IMAGE:
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=self._image_w, scale_y=self._image_h,
                              offset_x=0, offset_y=0)
        elif from_sys == CoordSystem.IMAGE and to_sys == CoordSystem.WORLD:
            mm_per_px = 1.0/self._px_per_mm if self._px_per_mm > 0 else 1.0
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=mm_per_px, scale_y=mm_per_px,
                              offset_x=0, offset_y=0)
        elif from_sys == CoordSystem.WORLD and to_sys == CoordSystem.IMAGE:
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=self._px_per_mm, scale_y=self._px_per_mm,
                              offset_x=0, offset_y=0)
        elif from_sys == CoordSystem.WORLD and to_sys == CoordSystem.NORMALIZED:
            # world → image → normalized
            t_img = self.get_transform(CoordSystem.WORLD, CoordSystem.IMAGE)
            t_norm = self.get_transform(CoordSystem.IMAGE, CoordSystem.NORMALIZED)
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=t_img.scale_x*t_norm.scale_x,
                              scale_y=t_img.scale_y*t_norm.scale_y,
                              offset_x=t_img.offset_x*t_norm.scale_x + t_norm.offset_x,
                              offset_y=t_img.offset_y*t_norm.scale_y + t_norm.offset_y)
        elif from_sys == CoordSystem.NORMALIZED and to_sys == CoordSystem.WORLD:
            t_img = self.get_transform(CoordSystem.NORMALIZED, CoordSystem.IMAGE)
            t_world = self.get_transform(CoordSystem.IMAGE, CoordSystem.WORLD)
            t = CoordTransform(from_system=from_sys, to_system=to_sys,
                              scale_x=t_img.scale_x*t_world.scale_x,
                              scale_y=t_img.scale_y*t_world.scale_y,
                              offset_x=t_img.offset_x*t_world.scale_x + t_world.offset_x,
                              offset_y=t_img.offset_y*t_world.scale_y + t_world.offset_y)
        else:
            # floor_local and building_global default to world
            t = CoordTransform(from_system=from_sys, to_system=to_sys, is_identity=True)

        self._transforms[key] = t
        # Also cache inverse
        inv = CoordTransform(from_system=to_sys, to_system=from_sys,
                            scale_x=1.0/t.scale_x if t.scale_x else 0,
                            scale_y=1.0/t.scale_y if t.scale_y else 0,
                            offset_x=-t.offset_x, offset_y=-t.offset_y)
        self._transforms[(to_sys, from_sys)] = inv
        return t

    def transform_point(self, pt: Point2D, from_sys: CoordSystem, to_sys: CoordSystem) -> Point2D:
        t = self.get_transform(from_sys, to_sys)
        if t.is_identity: return Point2D(x=pt.x, y=pt.y)
        return Point2D(x=pt.x*t.scale_x + t.offset_x, y=pt.y*t.scale_y + t.offset_y)

    def transform_points(self, pts: list[Point2D], from_sys: CoordSystem, to_sys: CoordSystem) -> list[Point2D]:
        return [self.transform_point(p, from_sys, to_sys) for p in pts]


# ═══════════════════════════════════════════════════════════
# Wall Reconstruction Engine
# ═══════════════════════════════════════════════════════════

class WallReconstructor:
    """Converts Phase 2 wall graph nodes into wall centerlines, bodies, and junctions."""

    MERGE_GAP_MM = 300.0         # max gap to consider for merging (pixels unless calibrated)
    SNAP_DISTANCE_MM = 500.0     # snap endpoints within this distance
    PARALLEL_ANGLE_TOL = 5.0     # degrees
    PERPENDICULAR_ANGLE_TOL = 5.0
    ORTHOGONAL_ANGLE_TOL = 2.0

    def __init__(self, coord_engine: CoordTransformEngine):
        self.coord = coord_engine

    def reconstruct(self, wall_graph_nodes: list[dict], scale_px_per_mm: float = 0.1) -> list[WallCenterline]:
        """
        Convert wall graph nodes into wall centerlines.
        Each wall_graph_node: {node_id, label, properties: {centerline, bbox, thickness_px, length_px}, confidence, ...}
        """
        centerlines = []

        for node in wall_graph_nodes:
            props = node.get("properties", {})
            cl_raw = props.get("centerline", [])

            # Convert centerline to Point2D list
            if cl_raw and len(cl_raw) >= 2:
                points = []
                for pt in cl_raw:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        points.append(Point2D(x=float(pt[0]), y=float(pt[1])))
                if len(points) >= 2:
                    cl = WallCenterline(
                        points=points,
                        graph_node_ref=UUID(node.get("node_id", "00000000-0000-0000-0000-000000000000")),
                        detection_ref=UUID(node.get("detection_ref", "00000000-0000-0000-0000-000000000000")) if node.get("detection_ref") else None,
                        confidence=node.get("confidence", 1.0),
                        source=node.get("source", ""),
                    )
                    centerlines.append(cl)
                    continue

            # Fallback: create centerline from bbox
            bbox = props.get("bbox", [])
            if bbox and len(bbox) >= 4:
                cx, cy = bbox[0] + bbox[2]/2, bbox[1] + bbox[3]/2
                # Determine primary direction from bbox aspect ratio
                if bbox[2] > bbox[3]:  # horizontal wall
                    points = [Point2D(x=bbox[0], y=cy), Point2D(x=bbox[0]+bbox[2], y=cy)]
                else:  # vertical wall
                    points = [Point2D(x=cx, y=bbox[1]), Point2D(x=cx, y=bbox[1]+bbox[3])]
                cl = WallCenterline(
                    points=points,
                    graph_node_ref=UUID(node.get("node_id", "00000000-0000-0000-0000-000000000000")),
                    confidence=node.get("confidence", 0.7),
                    state=GeometryState.INFERRED,
                    source=node.get("source", "bbox_fallback"),
                )
                centerlines.append(cl)

        return centerlines

    def merge_fragmented(self, centerlines: list[WallCenterline]) -> list[WallCenterline]:
        """Merge fragmented wall segments that are collinear and close."""
        if len(centerlines) < 2:
            return centerlines

        merged = []
        consumed = set()

        for i, cl_a in enumerate(centerlines):
            if i in consumed: continue
            merged_cl = cl_a
            for j, cl_b in enumerate(centerlines):
                if j <= i or j in consumed: continue
                if self._can_merge(merged_cl, cl_b):
                    merged_cl = self._merge_pair(merged_cl, cl_b)
                    consumed.add(j)
            merged.append(merged_cl)

        return merged

    def _can_merge(self, a: WallCenterline, b: WallCenterline) -> bool:
        """Check if two centerlines are collinear and endpoints are close."""
        if not a.points or not b.points: return False
        dir_a = (a.points[-1] - a.points[0]).normalized()
        dir_b = (b.points[-1] - b.points[0]).normalized()
        # Check collinearity
        dot = abs(dir_a.dot(dir_b))
        if dot < math.cos(math.radians(self.PARALLEL_ANGLE_TOL)):
            return False
        # Check endpoint proximity
        for pa in [a.points[0], a.points[-1]]:
            for pb in [b.points[0], b.points[-1]]:
                if pa.distance_to(pb) < self.MERGE_GAP_MM:
                    return True
        return False

    def _merge_pair(self, a: WallCenterline, b: WallCenterline) -> WallCenterline:
        """Merge two collinear centerlines."""
        all_pts = a.points + b.points
        # Order along direction vector
        dir_vec = (a.points[-1] - a.points[0]).normalized()
        proj = [(p.dot(dir_vec), p) for p in all_pts]
        proj.sort(key=lambda x: x[0])
        new_points = [p for _, p in proj]

        return WallCenterline(
            points=new_points,
            graph_node_ref=a.graph_node_ref,
            confidence=min(a.confidence, b.confidence),
            state=GeometryState.INFERRED,
            source="merged",
        )

    def snap_endpoints(self, centerlines: list[WallCenterline]) -> list[WallCenterline]:
        """Snap nearby endpoints together."""
        for i in range(len(centerlines)):
            for j in range(i+1, len(centerlines)):
                cl_a, cl_b = centerlines[i], centerlines[j]
                for ei, ep_a in enumerate([0, -1]):
                    for ej, ep_b in enumerate([0, -1]):
                        if cl_a.points[ei].distance_to(cl_b.points[ej]) < self.SNAP_DISTANCE_MM:
                            # Average position
                            mid = Point2D(
                                x=(cl_a.points[ei].x + cl_b.points[ej].x)/2,
                                y=(cl_a.points[ei].y + cl_b.points[ej].y)/2
                            )
                            if ei == 0: cl_a.points[0] = mid
                            else: cl_a.points[-1] = mid
                            if ej == 0: cl_b.points[0] = mid
                            else: cl_b.points[-1] = mid
        return centerlines

    def split_intersecting(self, centerlines: list[WallCenterline]) -> list[WallCenterline]:
        """Split walls that intersect."""
        result = []
        for i, cl in enumerate(centerlines):
            segments = cl.as_lines()
            split_points = []
            for j, other in enumerate(centerlines):
                if i == j: continue
                for seg in segments:
                    other_segs = other.as_lines()
                    for oseg in other_segs:
                        inter = seg.intersection(oseg)
                        if inter:
                            split_points.append(inter)
            if not split_points:
                result.append(cl)
            else:
                # Sort split points along wall direction
                all_pts = cl.points + split_points
                dir_vec = (cl.points[-1] - cl.points[0]).normalized()
                proj = [(p.dot(dir_vec), p) for p in all_pts]
                proj.sort(key=lambda x: x[0])
                seen = set()
                unique = []
                for _, p in proj:
                    key = (round(p.x, 3), round(p.y, 3))
                    if key not in seen:
                        seen.add(key)
                        unique.append(p)
                result.append(WallCenterline(
                    points=unique,
                    graph_node_ref=cl.graph_node_ref,
                    confidence=cl.confidence,
                    state=cl.state,
                    source=cl.source + "+split",
                ))
        return result

    def create_junctions(self, centerlines: list[WallCenterline]) -> list[WallJunction]:
        """Identify wall junctions from centerline endpoints/intersections."""
        junctions = []
        # Collect all endpoints and intersection points
        endpoint_map: dict[tuple[int,int], list[UUID]] = {}
        tol = int(self.SNAP_DISTANCE_MM)

        for cl in centerlines:
            for pt in [cl.points[0], cl.points[-1]]:
                key = (int(pt.x/tol), int(pt.y/tol))
                if key not in endpoint_map:
                    endpoint_map[key] = []
                endpoint_map[key].append(cl.centerline_id)

        # Create junctions
        for key, wall_ids in endpoint_map.items():
            if len(wall_ids) < 2:
                continue
            # Calculate average position
            pts = []
            for wid in wall_ids:
                cl = next((c for c in centerlines if c.centerline_id == wid), None)
                if cl:
                    for pt in [cl.points[0], cl.points[-1]]:
                        pt_key = (int(pt.x/tol), int(pt.y/tol))
                        if pt_key == key:
                            pts.append(pt)
            if not pts: continue
            avg_pos = Point2D(x=sum(p.x for p in pts)/len(pts), y=sum(p.y for p in pts)/len(pts))

            # Determine junction type
            n = len(set(wall_ids))
            if n == 2:
                # Check angle between walls
                w1 = next((c for c in centerlines if c.centerline_id == wall_ids[0]), None)
                w2 = next((c for c in centerlines if c.centerline_id == wall_ids[1]), None)
                if w1 and w2:
                    d1 = w1.points[-1] - w1.points[0]
                    d2 = w2.points[-1] - w2.points[0]
                    angle = abs(math.degrees(math.acos(max(-1, min(1, d1.normalized().dot(d2.normalized()))))))
                    if angle < 15: jt = JunctionType.ENDPOINT
                    elif 75 < angle < 105: jt = JunctionType.L
                    else: jt = JunctionType.CORNER
                else:
                    jt = JunctionType.ENDPOINT
            elif n == 3:
                jt = JunctionType.T
            elif n >= 4:
                jt = JunctionType.X if n == 4 else JunctionType.MULTI
            else:
                jt = JunctionType.ENDPOINT

            junctions.append(WallJunction(
                junction_type=jt,
                position=avg_pos,
                wall_ids=[wid for wid in wall_ids],
                confidence=0.85,
            ))

        return junctions

    def classify_walls(self, centerlines: list[WallCenterline], room_boundaries: list[list[Point2D]] = None) -> list[WallCenterline]:
        """Classify walls as internal or external."""
        for cl in centerlines:
            mid = cl.midpoint()
            # Simple heuristic: if wall midpoint is near the outer bbox boundary, it's external
            all_pts = [p for c in centerlines for p in c.points]
            if not all_pts: continue
            bbox = BoundingBox2D.from_points(all_pts)
            margin = bbox.width() * 0.1
            if (abs(mid.x - bbox.min_x) < margin or abs(mid.x - bbox.max_x) < margin or
                abs(mid.y - bbox.min_y) < margin or abs(mid.y - bbox.max_y) < margin):
                cl.is_external = True
        return centerlines


# ═══════════════════════════════════════════════════════════
# Wall Body Builder
# ═══════════════════════════════════════════════════════════

class WallBodyBuilder:
    """Creates wall bodies from centerlines and thickness."""

    def build(self, centerline: WallCenterline, thickness_mm: float) -> WallBody:
        """Create wall body polygon from centerline and thickness."""
        if len(centerline.points) < 2:
            return WallBody(
                centerline_id=centerline.centerline_id,
                centerline=centerline.points,
                thickness=thickness_mm,
                confidence=centerline.confidence,
                state=centerline.state,
                source_graph_ref=centerline.graph_node_ref,
            )

        half = thickness_mm / 2

        # For wall body, offset centerline to both sides and close the polygon
        pts = centerline.points
        faces_left = []
        faces_right = []

        for i, pt in enumerate(pts):
            # Direction at this point
            if i == 0:
                d = (pts[1] - pts[0]).normalized()
            elif i == len(pts) - 1:
                d = (pts[-1] - pts[-2]).normalized()
            else:
                d1 = (pts[i] - pts[i-1]).normalized()
                d2 = (pts[i+1] - pts[i]).normalized()
                d = (d1 + d2).normalized()

            perp = Point2D(x=-d.y, y=d.x)
            faces_left.append(Point2D(x=pt.x + perp.x*half, y=pt.y + perp.y*half))
            faces_right.append(Point2D(x=pt.x - perp.x*half, y=pt.y - perp.y*half))

        # Build closed polygon: left face forward + right face backward
        polygon = faces_left + list(reversed(faces_right))

        return WallBody(
            centerline_id=centerline.centerline_id,
            centerline=pts,
            face_left=faces_left,
            face_right=faces_right,
            thickness=thickness_mm,
            polygon=polygon,
            is_external=centerline.is_external,
            confidence=centerline.confidence,
            state=centerline.state,
            source_graph_ref=centerline.graph_node_ref,
        )


# Singleton
coord_engine = CoordTransformEngine(image_width=1200, image_height=800, px_per_mm=5.9)
wall_reconstructor = WallReconstructor(coord_engine)
wall_body_builder = WallBodyBuilder()
