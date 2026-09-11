#!/usr/bin/env python3
"""
Vision 5D — CAD Fidelity Bridge
Direct CAD-to-understanding-graph pipeline that preserves wall segments,
room boundaries, doors, and windows without the lossy CV rendering step.
"""
import os, sys, json, math
from uuid import uuid4
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.cad_import.dxf_parser import DXFParser, extract_walls_from_cad, extract_doors_from_cad, extract_rooms_from_cad


@dataclass
class WallSegment:
    id: str
    x1: float; y1: float; x2: float; y2: float
    thickness: float = 120.0
    is_exterior: bool = True
    connected_doors: list = field(default_factory=list)
    connected_windows: list = field(default_factory=list)


@dataclass
class RoomBoundary:
    id: str
    label: str
    polygon: list  # [(x,y), ...]
    area_mm2: float = 0.0
    walls: list = field(default_factory=list)
    doors: list = field(default_factory=list)
    windows: list = field(default_factory=list)


@dataclass
class Opening:
    id: str
    opening_type: str  # door, window
    x: float; y: float
    width: float = 900.0
    rotation_deg: float = 0.0
    wall_id: str = ""


class CADFidelityBridge:
    """
    Preserves CAD fidelity by working directly with vector data
    rather than rasterizing to an image for CV processing.
    """

    def __init__(self, drawing, scale: float = 1.0):
        self.drawing = drawing
        self.scale = scale
        self.walls: list[WallSegment] = []
        self.rooms: list[RoomBoundary] = []
        self.doors: list[Opening] = []
        self.windows: list[Opening] = []
        self.room_polygons: list = []  # From A-ROOM layer

    def extract_all(self):
        """Extract all architectural elements with fidelity preservation."""
        parser = DXFParser()

        # Extract walls from CAD entities (preserve ALL segments)
        raw_walls = extract_walls_from_cad(self.drawing, parser)
        self.walls = self._process_walls(raw_walls)

        # Extract doors from INSERT blocks
        raw_doors = extract_doors_from_cad(self.drawing, parser)
        self.doors = self._process_openings(raw_doors, "door")

        # Extract windows from LINE entities on WINDOW layer
        classified = parser.classify_layers(self.drawing)
        raw_windows = [{"id": uuid4().hex[:12], "layer": e.layer,
                        "position": (e.points[0] if e.points else (0, 0)), "width": 1200}
                       for e in classified["windows"]]
        self.windows = self._process_openings(raw_windows, "window")

        # Extract room polygons from A-ROOM layer
        room_polys = []
        for e in classified["rooms"]:
            if e.closed and len(e.points) >= 3:
                room_polys.append({"id": uuid4().hex[:12], "label": f"Room_{len(room_polys)+1}",
                                   "polygon": e.points, "layer": e.layer})

        # Extract room labels from TEXT
        text_labels = []
        for e in classified["text"]:
            if e.text and e.points:
                text_labels.append({"label": e.text, "position": e.points[0]})

        # Match room labels to polygons by point-in-polygon
        self.rooms = self._match_rooms(room_polys, text_labels)

        # Associate doors/windows with walls
        self._associate_openings_with_walls()

        return self

    def _process_walls(self, raw_walls: list) -> list[WallSegment]:
        """Process raw wall lines into clean wall segments."""
        segments = []
        for w in raw_walls:
            pts = w.get("points", [])
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                # Skip degenerate segments (use small threshold since some CADs use meters)
                if math.hypot(x2 - x1, y2 - y1) < 0.1:
                    continue
                ws = WallSegment(
                    id=uuid4().hex[:8],
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    thickness=w.get("thickness", 120.0),
                    is_exterior=self._is_exterior(x1, y1, x2, y2),
                )
                segments.append(ws)
        return segments

    def _process_openings(self, raw_openings: list, opening_type: str) -> list[Opening]:
        """Convert raw openings to structured Opening objects."""
        openings = []
        for o in raw_openings:
            pos = o.get("position", (0, 0))
            openings.append(Opening(
                id=o.get("id", uuid4().hex[:8]),
                opening_type=opening_type,
                x=pos[0], y=pos[1],
                width=o.get("width", 900 if opening_type == "door" else 1200),
                rotation_deg=0,
            ))
        return openings

    def _match_rooms(self, polygons: list, labels: list) -> list[RoomBoundary]:
        """Match text labels to room polygons."""
        rooms = []

        for poly in polygons:
            # Find nearest label
            best_label = poly["label"]
            best_dist = float("inf")
            cx = sum(p[0] for p in poly["polygon"]) / len(poly["polygon"])
            cy = sum(p[1] for p in poly["polygon"]) / len(poly["polygon"])

            for lbl in labels:
                lx, ly = lbl["position"]
                dist = math.hypot(lx - cx, ly - cy)
                if dist < best_dist:
                    best_dist = dist
                    best_label = lbl["label"]

            area = self._polygon_area(poly["polygon"])
            rooms.append(RoomBoundary(
                id=poly["id"],
                label=best_label,
                polygon=poly["polygon"],
                area_mm2=area,
                walls=[],
            ))

        # Any labels without matching polygon → floating, add as room
        matched_labels = {r.label for r in rooms}
        for lbl in labels:
            if lbl["label"] not in matched_labels and lbl["label"] not in ("12000", "9000", "900"):  # Skip dims
                rooms.append(RoomBoundary(
                    id=uuid4().hex[:8],
                    label=lbl["label"],
                    polygon=[(lbl["position"][0]-500, lbl["position"][1]-500),
                            (lbl["position"][0]+500, lbl["position"][1]-500),
                            (lbl["position"][0]+500, lbl["position"][1]+500),
                            (lbl["position"][0]-500, lbl["position"][1]+500)],
                    area_mm2=1_000_000,  # ~1m² placeholder
                    walls=[],
                ))

        return rooms

    def _associate_openings_with_walls(self):
        """Associate doors and windows with the nearest wall segment."""
        for opening in (self.doors + self.windows):
            best_wall = None
            best_dist = float("inf")

            for wall in self.walls:
                # Distance from point to line segment
                dist = self._point_to_segment_distance(
                    opening.x, opening.y, wall.x1, wall.y1, wall.x2, wall.y2
                )
                if dist < best_dist:
                    best_dist = dist
                    best_wall = wall

            if best_wall and best_dist < 2000:
                opening.wall_id = best_wall.id
                if opening.opening_type == "door":
                    best_wall.connected_doors.append(opening.id)
                else:
                    best_wall.connected_windows.append(opening.id)

    def _is_exterior(self, x1, y1, x2, y2) -> bool:
        """Determine if a wall is exterior by proximity to drawing bounds."""
        margin = 100
        b = self.drawing.bounds
        return (abs(x1 - b[0]) < margin or abs(x1 - b[2]) < margin or
                abs(y1 - b[1]) < margin or abs(y1 - b[3]) < margin or
                abs(x2 - b[0]) < margin or abs(x2 - b[2]) < margin or
                abs(y2 - b[1]) < margin or abs(y2 - b[3]) < margin)

    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        """Distance from point to line segment."""
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    def _polygon_area(self, points):
        n = len(points)
        if n < 3: return 0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1] - points[j][0] * points[i][1]
        return abs(area) / 2.0

    def generate_interior_wall_image(self, width=1200, height=800):
        """Generate a high-fidelity architectural image from vector data.
        Uses separate colors for walls, doors, and room labels.
        Uses thinner lines to prevent wall merging.
        """
        try:
            import cv2, numpy as np
            img = np.ones((height, width, 3), dtype=np.uint8) * 255
        except ImportError:
            import numpy as np
            return np.ones((height, width, 3), dtype=np.uint8) * 255

        # Scale factors
            dw = self.drawing.width
            dh = self.drawing.height
            if dw <= 0 or dh <= 0:
                return img
            sx = (width - 40) / dw
            sy = (height - 40) / dh
            s = min(sx, sy)
            ox = (width - dw * s) / 2
            oy = (height - dh * s) / 2

            def to_px(x, y):
                return int(ox + x * s), int(oy + y * s)

            # Draw room polygons as light fill
            for room in self.rooms:
                pts = np.array([to_px(p[0], p[1]) for p in room.polygon], dtype=np.int32)
                if len(pts) >= 3:
                    cv2.fillPoly(img, [pts], (245, 250, 245))  # Light green
                    cv2.polylines(img, [pts], True, (180, 200, 180), 1)

            # Draw walls (thin, dark lines — 2px at scale)
            for wall in self.walls:
                p1 = to_px(wall.x1, wall.y1)
                p2 = to_px(wall.x2, wall.y2)
                color = (30, 30, 30) if wall.is_exterior else (80, 80, 80)
                cv2.line(img, p1, p2, color, 2)

            # Draw doors (blue dots)
            for door in self.doors:
                p = to_px(door.x, door.y)
                cv2.circle(img, p, 5, (0, 100, 200), -1)

            # Draw windows (blue lines)
            for win in self.windows:
                p = to_px(win.x, win.y)
                cv2.circle(img, p, 4, (100, 150, 200), -1)

            # Draw room labels
            for room in self.rooms:
                cx = sum(p[0] for p in room.polygon) / max(len(room.polygon), 1)
                cy = sum(p[1] for p in room.polygon) / max(len(room.polygon), 1)
                p = to_px(cx, cy)
                cv2.putText(img, room.label[:15], (p[0]-30, p[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

            return img
        except ImportError:
            import numpy as np
            return np.ones((height, width, 3), dtype=np.uint8) * 255


# ── Convenience runner ──

def run_fidelity_bridge(dxf_content: str):
    """Run the full fidelity bridge on a DXF file."""
    parser = DXFParser()
    drawing = parser.parse(dxf_content)

    bridge = CADFidelityBridge(drawing)
    bridge.extract_all()

    print(f"=== CAD FIDELITY BRIDGE RESULTS ===")
    print(f"  Walls:    {len(bridge.walls)} segments")
    print(f"  Rooms:    {len(bridge.rooms)} ({', '.join(r.label for r in bridge.rooms)})")
    print(f"  Doors:    {len(bridge.doors)}")
    print(f"  Windows:  {len(bridge.windows)}")
    print(f"  Exterior walls: {sum(1 for w in bridge.walls if w.is_exterior)}")
    print(f"  Interior walls: {sum(1 for w in bridge.walls if not w.is_exterior)}")

    # Wall-to-room association rate
    total_walls = len(bridge.walls)
    associated = sum(1 for w in bridge.walls if w.connected_doors or w.connected_windows)
    print(f"  Wall-opening assoc: {associated}/{total_walls} walls")

    return bridge
