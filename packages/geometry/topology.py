"""
Vision 5D — Phase 3 Topology Engine
"""
from uuid import UUID, uuid4
from packages.geometry.contracts import (
    TopologyGraph, TopologyEdge, TopologyRelation,
    WallBody, RoomGeometry, Opening, OpeningType,
    Point2D, Polygon2D,
)


class TopologyEngine:
    """Builds authoritative architectural topology from geometry."""

    def build(self, walls: list[WallBody], rooms: list[RoomGeometry],
              openings: list[Opening]) -> TopologyGraph:
        topology = TopologyGraph()
        issues = []

        # Room containment (rooms within floor - implicit)
        # Room adjacency (shared walls)
        for i, ra in enumerate(rooms):
            for rb in rooms[i+1:]:
                shared = set(ra.wall_ids) & set(rb.wall_ids)
                shared_opens = set(ra.opening_ids) & set(rb.opening_ids)
                if shared or shared_opens:
                    topology.edges.append(TopologyEdge(
                        source_id=ra.room_id, target_id=rb.room_id,
                        relation=TopologyRelation.ADJACENT_TO,
                        shared_wall_ids=list(shared),
                        shared_opening_ids=list(shared_opens),
                        confidence=0.80,
                    ))

        # Opening connectivity (door connects rooms)
        for op in openings:
            if op.opening_type == OpeningType.DOOR and op.is_valid:
                if op.connects_room_a and op.connects_room_b:
                    topology.edges.append(TopologyEdge(
                        source_id=op.connects_room_a, target_id=op.connects_room_b,
                        relation=TopologyRelation.CONNECTED_BY,
                        shared_opening_ids=[op.opening_id],
                        confidence=op.confidence,
                    ))

        # Opening-to-wall: CONNECTED_BY
        for op in openings:
            if op.host_wall_id:
                # Find wall body
                wall = next((w for w in walls if w.centerline_id == op.host_wall_id), None)
                if wall:
                    topology.edges.append(TopologyEdge(
                        source_id=op.opening_id, target_id=wall.body_id,
                        relation=TopologyRelation.CONNECTED_BY,
                        confidence=op.confidence,
                    ))

        # Detect issues
        issues.extend(self._detect_issues(walls, rooms, openings))
        topology.issues = issues
        topology.is_consistent = len(issues) == 0

        # Find disconnected components
        topology.disconnected_components = self._find_disconnected(rooms)

        return topology

    def _detect_issues(self, walls: list[WallBody], rooms: list[RoomGeometry],
                       openings: list[Opening]) -> list[str]:
        issues = []

        # Isolated walls
        for w in walls:
            connected = False
            for r in rooms:
                if w.body_id in r.wall_ids:
                    connected = True
                    break
            for op in openings:
                if op.host_wall_id == w.centerline_id:
                    connected = True
                    break
            if not connected:
                issues.append(f"Isolated wall: {w.body_id}")

        # Dangling endpoints
        endpoint_count: dict[tuple[int,int], int] = {}
        for w in walls:
            for pt in w.centerline[:1] + w.centerline[-1:]:
                key = (int(pt.x/10), int(pt.y/10))
                endpoint_count[key] = endpoint_count.get(key, 0) + 1
        for key, count in endpoint_count.items():
            if count == 1:
                issues.append(f"Dangling wall endpoint near ({key[0]*10}, {key[1]*10})")

        # Disconnected rooms
        connected_rooms = set()
        for edge in self._adjacency_edges:
            pass  # populated during adjacency detection

        # Zero-area rooms
        for r in rooms:
            if r.area_mm2 < 100:  # less than 1cm²
                issues.append(f"Zero-area room: {r.label or r.room_id}")

        # Self-intersecting polygons
        for r in rooms:
            if len(r.polygon) >= 3:
                poly = Polygon2D(vertices=r.polygon)
                if not poly.is_valid():
                    issues.append(f"Self-intersecting room polygon: {r.label or r.room_id}")

        # Invalid opening hosts
        for op in openings:
            if op.host_wall_id and not op.is_valid:
                issues.append(f"Invalid opening placement: {op.opening_id}")

        # Overlapping rooms
        for i, ra in enumerate(rooms):
            poly_a = Polygon2D(vertices=ra.polygon)
            for rb in rooms[i+1:]:
                poly_b = Polygon2D(vertices=rb.polygon)
                if self._polygons_overlap(poly_a, poly_b):
                    ra_shared = set(ra.wall_ids) & set(rb.wall_ids)
                    if not ra_shared:
                        issues.append(f"Overlapping rooms: {ra.label} and {rb.label}")

        return issues

    @staticmethod
    def _polygons_overlap(a: Polygon2D, b: Polygon2D) -> bool:
        """Check if two polygons overlap (simple centroid distance heuristic)."""
        ca, cb = a.centroid(), b.centroid()
        return ca.distance_to(cb) < 100  # rough heuristic

    @staticmethod
    def _find_disconnected(rooms: list[RoomGeometry]) -> list[list[UUID]]:
        """Find rooms that are not connected to any other room."""
        if not rooms: return []
        adj = {r.room_id: set() for r in rooms}
        for r in rooms:
            for aid in r.adjacent_room_ids:
                adj[r.room_id].add(aid)
                if aid in adj:
                    adj[aid].add(r.room_id)

        visited = set()
        components = []
        for r in rooms:
            if r.room_id not in visited:
                comp = []
                stack = [r.room_id]
                while stack:
                    nid = stack.pop()
                    if nid in visited: continue
                    visited.add(nid)
                    comp.append(nid)
                    for neighbor in adj.get(nid, set()):
                        if neighbor not in visited:
                            stack.append(neighbor)
                components.append(comp)
        return [c for c in components if len(c) == 1]  # only truly disconnected

    _adjacency_edges: list[TopologyEdge] = []


topology_engine = TopologyEngine()
