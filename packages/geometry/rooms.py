"""
Vision 5D — Phase 3 Room Polygon Engine
"""
from uuid import UUID, uuid4
import math
from packages.geometry.contracts import (
    Point2D, Line2D, Polygon2D, BoundingBox2D,
    RoomGeometry, WallBody, Opening, WallCenterline,
    GeometryState,
)


class RoomPolygonEngine:
    """Generates room polygons from reconstructed walls and openings."""

    def generate(self, walls: list[WallBody], openings: list[Opening],
                 room_nodes: list[dict], wall_centerlines: list[WallCenterline]) -> list[RoomGeometry]:
        rooms = []
        for room_node in room_nodes:
            props = room_node.get("properties", {})
            label = room_node.get("label", "")
            function = props.get("function", "unknown")
            node_id = UUID(room_node.get("node_id", str(uuid4())))

            room_wall_ids = props.get("wall_ids", []) or room_node.get("wall_ids", [])
            room_opening_ids = props.get("opening_ids", []) or room_node.get("opening_ids", [])

            boundary_walls = [w for w in walls
                            if str(w.centerline_id) in [str(wid) for wid in room_wall_ids]]
            if not boundary_walls:
                boundary_walls = self._find_enclosing_walls(walls, room_node)

            polygon = self._build_polygon_from_walls(boundary_walls)
            if not polygon or len(polygon) < 3:
                cl_for_room = [cl for cl in wall_centerlines
                              if str(cl.centerline_id) in [str(wid) for wid in room_wall_ids]]
                polygon = self._build_polygon_from_centerlines(cl_for_room)

            poly = Polygon2D(vertices=polygon)
            area = poly.area()
            centroid = poly.centroid()
            is_closed = len(polygon) >= 3 and polygon[0].distance_to(polygon[-1]) < 5.0

            room = RoomGeometry(
                room_id=uuid4(),
                label=label,
                function=function,
                polygon=polygon,
                area_mm2=area,
                perimeter_mm=poly.perimeter(),
                centroid=centroid,
                wall_ids=[w.body_id for w in boundary_walls],
                opening_ids=[UUID(oid) for oid in room_opening_ids],
                graph_node_ref=node_id,
                confidence=room_node.get("confidence", 0.8),
                state=GeometryState.INFERRED,
                is_closed=is_closed,
            )
            room.validate_closure()
            rooms.append(room)

        self._detect_adjacency(rooms)
        return rooms

    def _find_enclosing_walls(self, walls: list[WallBody], room_node: dict) -> list[WallBody]:
        props = room_node.get("properties", {})
        bbox = props.get("bbox", [])
        if not bbox or len(bbox) < 4:
            return walls[:4] if len(walls) >= 4 else walls
        room_bbox = BoundingBox2D(min_x=bbox[0], min_y=bbox[1],
                                   max_x=bbox[0]+bbox[2], max_y=bbox[1]+bbox[3])
        return [w for w in walls if self._wall_intersects_bbox(w, room_bbox)]

    @staticmethod
    def _wall_intersects_bbox(wall: WallBody, bbox: BoundingBox2D) -> bool:
        for pt in wall.centerline:
            if bbox.contains(pt):
                return True
        return False

    @staticmethod
    def _build_polygon_from_walls(walls: list[WallBody]) -> list[Point2D]:
        if not walls: return []
        all_pts = []
        for w in walls:
            all_pts.extend(w.centerline)
        if not all_pts: return []
        return RoomPolygonEngine._convex_hull(all_pts)

    @staticmethod
    def _build_polygon_from_centerlines(cls: list[WallCenterline]) -> list[Point2D]:
        if not cls: return []
        pts = []
        for cl in cls:
            pts.extend(cl.points)
        if not pts: return []
        return RoomPolygonEngine._convex_hull(pts)

    @staticmethod
    def _convex_hull(points: list[Point2D]) -> list[Point2D]:
        if len(points) <= 3: return points
        pts = sorted(points, key=lambda p: (p.y, p.x))
        p0 = pts[0]

        def angle(p):
            return math.atan2(p.y - p0.y, p.x - p0.x)

        sorted_pts = sorted(pts[1:], key=angle)
        hull = [p0]
        for p in sorted_pts:
            while len(hull) >= 2:
                a, b = hull[-2], hull[-1]
                cross = (b.x - a.x)*(p.y - a.y) - (b.y - a.y)*(p.x - a.x)
                if cross > 0: break
                hull.pop()
            hull.append(p)
        return hull

    @staticmethod
    def _detect_adjacency(rooms: list[RoomGeometry]):
        for i, ra in enumerate(rooms):
            for rb in rooms[i+1:]:
                shared = set(ra.wall_ids) & set(rb.wall_ids)
                if shared:
                    ra.adjacent_room_ids.append(rb.room_id)
                    rb.adjacent_room_ids.append(ra.room_id)


room_engine = RoomPolygonEngine()
