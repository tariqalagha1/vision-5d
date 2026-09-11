"""
Vision 5D — DXF CAD Import Module
Parses real architectural DXF/DWG files into structured geometry.
"""
import math, re, structlog
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Optional

logger = structlog.get_logger()


@dataclass
class CADEntity:
    entity_type: str
    layer: str = "0"
    color: int = 7
    points: list = field(default_factory=list)
    radius: float = 0.0
    text: str = ""
    rotation: float = 0.0
    closed: bool = False
    thickness: float = 0.0
    properties: dict = field(default_factory=dict)


@dataclass
class CADDrawing:
    filename: str = ""
    entities: list = field(default_factory=list)
    layers: set = field(default_factory=set)
    bounds: tuple = (0, 0, 0, 0)
    units: str = "mm"
    scale: float = 1.0
    insunits: int = 0  # DXF $INSUNITS group-code value (0=unitless, 1=inches, 4=mm, 6=meters…)

    @property
    def width(self):
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self):
        return self.bounds[3] - self.bounds[1]


class DXFParser:
    WALL_LAYERS = ["wall", "a-wall", "a_wall", "masonry", "partition"]
    DOOR_LAYERS = ["door", "a-door", "a_door", "opening-door"]
    WINDOW_LAYERS = ["window", "a-window", "a_window", "glazing", "ventana", "fenetre", "fen", "glaz", "vid"]
    DIM_LAYERS = ["dim", "dimension", "a-anno-dim", "a_dim"]
    TEXT_LAYERS = ["text", "a-anno-text", "a_text", "label", "room-name", "room_label"]
    ROOM_LAYERS = ["room", "a-area", "a_area", "space", "hatch"]

    def parse(self, dxf_content: str) -> CADDrawing:
        drawing = CADDrawing()
        if not dxf_content.strip():
            return drawing
        lines = dxf_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # NOTE: do NOT strip empty lines. DXF group values can legitimately be
        # empty strings (e.g. "$DIMBLK" with no value), and LibreDWG-generated
        # DXFs rely on those empty value lines — stripping them desyncs the
        # (code, value) pairing and the whole ENTITIES section parses to zero.

        # Capture $INSUNITS (drawing unit system) from the HEADER section.
        m = re.search(r'\$INSUNITS\s*\n\s*(\d+)', dxf_content)
        if m:
            try:
                drawing.insunits = int(m.group(1))
            except ValueError:
                drawing.insunits = 0

        return self._parse_ascii_dxf(lines, drawing)

    def _parse_ascii_dxf(self, lines: list, drawing: CADDrawing) -> CADDrawing:
        i = 0
        current_entity = None
        current_section = ""
        vertex_points = []
        polyline_layer = "0"
        polyline_closed = False
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        while i < len(lines) - 1:
            code = lines[i].strip()
            value = lines[i + 1].strip()

            # Skip comments (group code 999)
            if code == "999":
                i += 2; continue

            if code == "0":
                if value == "SECTION": pass
                elif value == "ENDSEC": current_section = ""
                elif current_section == "ENTITIES" and value not in ("ENDSEC",):
                    # Flush previous entity
                    if current_entity and current_entity.entity_type == "LWPOLYLINE" and vertex_points:
                        current_entity.points = [(p[0], p[1]) for p in vertex_points]
                        current_entity.closed = polyline_closed
                    if current_entity:
                        drawing.entities.append(current_entity)
                        drawing.layers.add(current_entity.layer)
                        for px, py in current_entity.points if isinstance(current_entity.points, list) else []:
                            if isinstance(px, (int, float)) and isinstance(py, (int, float)):
                                min_x = min(min_x, px); max_x = max(max_x, px)
                                min_y = min(min_y, py); max_y = max(max_y, py)

                    # Start new entity
                    et = value
                    if et in ("LINE", "CIRCLE", "ARC", "TEXT", "MTEXT", "INSERT"):
                        current_entity = CADEntity(entity_type=et)
                    elif et == "LWPOLYLINE":
                        current_entity = CADEntity(entity_type="LWPOLYLINE")
                        vertex_points = []; polyline_closed = False; polyline_layer = "0"
                    elif et == "POLYLINE":
                        current_entity = CADEntity(entity_type="POLYLINE")
                        vertex_points = []; polyline_closed = False; polyline_layer = "0"
                    elif et == "VERTEX":
                        current_entity = CADEntity(entity_type="VERTEX")
                    elif et == "SEQEND":
                        if vertex_points:
                            ent = CADEntity(entity_type="POLYLINE", layer=polyline_layer,
                                           points=vertex_points, closed=polyline_closed)
                            drawing.entities.append(ent)
                            drawing.layers.add(polyline_layer)
                            for px, py in vertex_points:
                                min_x = min(min_x, px); max_x = max(max_x, px)
                                min_y = min(min_y, py); max_y = max(max_y, py)
                        vertex_points = []
                        current_entity = None
                    else:
                        current_entity = None
                    i += 2; continue

            if code == "2":
                if value in ("ENTITIES", "BLOCKS", "TABLES", "HEADER"):
                    current_section = value
                i += 2; continue

            # Entity properties
            if current_entity:
                if code == "8":
                    current_entity.layer = value
                    if current_entity.entity_type in ("LWPOLYLINE", "POLYLINE"):
                        polyline_layer = value
                elif code == "62":
                    try: current_entity.color = int(value)
                    except: pass
                elif code == "10":
                    current_entity.points.append((float(value), 0))
                elif code == "20" and current_entity.points:
                    current_entity.points[-1] = (current_entity.points[-1][0], float(value))
                elif code == "40":
                    current_entity.radius = float(value)
                elif code in ("1", "3"):
                    current_entity.text = value
                elif code == "50":
                    current_entity.rotation = math.radians(float(value))
                elif code == "51":
                    # ARC end angle
                    current_entity.properties["end_angle"] = math.radians(float(value))
                elif code == "42":
                    # LWPOLYLINE bulge (arc segment). Store per-vertex list.
                    try:
                        bulges = current_entity.properties.setdefault("bulges", [])
                        bulges.append(float(value))
                    except Exception:
                        pass
                elif code == "70":
                    flags = int(value)
                    if current_entity.entity_type in ("LWPOLYLINE", "POLYLINE"):
                        polyline_closed = bool(flags & 1)
                elif code == "90" and current_entity.entity_type == "LWPOLYLINE":
                    vertex_points = []
                elif code == "11":
                    if len(current_entity.points) >= 1:
                        current_entity.points.append((float(value), 0))
                elif code == "21" and len(current_entity.points) >= 2:
                    current_entity.points[-1] = (current_entity.points[-1][0], float(value))

                # LWPOLYLINE vertex accumulation
                if current_entity.entity_type == "LWPOLYLINE":
                    if code == "10":
                        vertex_points.append([float(value), 0])
                    elif code == "20" and vertex_points:
                        vertex_points[-1][1] = float(value)

            i += 2

        # Flush last entity
        if current_entity:
            if current_entity.entity_type == "LWPOLYLINE" and vertex_points:
                current_entity.points = [(p[0], p[1]) for p in vertex_points]
            drawing.entities.append(current_entity)
            drawing.layers.add(current_entity.layer)

        drawing.bounds = (min_x, min_y, max_x, max_y)
        return drawing

    def classify_layers(self, drawing: CADDrawing) -> dict:
        classified = {"walls": [], "doors": [], "windows": [], "dimensions": [], "text": [], "rooms": [], "unknown": []}
        for entity in drawing.entities:
            ll = entity.layer.lower()
            is_wall = any(p in ll for p in self.WALL_LAYERS)
            is_door = any(p in ll for p in self.DOOR_LAYERS)
            is_window = any(p in ll for p in self.WINDOW_LAYERS)
            if is_wall:
                classified["walls"].append(entity)
            elif is_door and is_window:
                # Combined door+window layer (e.g. "DOOR WINDOW 1 75"). Heuristic:
                # door swings/blocks (ARC/CIRCLE/INSERT) and single-line leaves
                # (LINE) are doors; multi-segment frames (LWPOLYLINE/POLYLINE)
                # are windows. Without block resolution this can't be exact, but
                # it keeps BOTH openings populated instead of dropping windows.
                if entity.entity_type in ("ARC", "CIRCLE", "INSERT", "LINE"):
                    classified["doors"].append(entity)
                else:
                    classified["windows"].append(entity)
            elif is_door:
                classified["doors"].append(entity)
            elif is_window:
                classified["windows"].append(entity)
            elif any(p in ll for p in self.DIM_LAYERS):
                classified["dimensions"].append(entity)
            elif any(p in ll for p in self.TEXT_LAYERS):
                classified["text"].append(entity)
            elif any(p in ll for p in self.ROOM_LAYERS):
                classified["rooms"].append(entity)
            elif entity.entity_type in ("LINE", "LWPOLYLINE", "POLYLINE"):
                classified["walls"].append(entity)
            else:
                classified["unknown"].append(entity)
        return classified

    # $INSUNITS → scale factor to convert drawing units → millimeters
    INSUNITS_TO_MM = {
        0: 1.0,     # unitless
        1: 25.4,    # inches
        2: 304.8,   # feet
        4: 1.0,     # millimeters
        5: 10.0,    # centimeters
        6: 1000.0,  # meters
    }

    def detect_scale(self, drawing: CADDrawing) -> float:
        """Return the scale factor that converts drawing units to millimeters."""
        if drawing.insunits in self.INSUNITS_TO_MM:
            return self.INSUNITS_TO_MM[drawing.insunits]
        # Unknown / non-standard $INSUNITS (e.g. 70 from LibreDWG): fall back to
        # a size heuristic. A sub-100-unit drawing is almost certainly in meters.
        if drawing.width < 100:
            return 1000.0
        return 1.0


def extract_walls_from_cad(drawing: CADDrawing, parser=None):
    if parser is None: parser = DXFParser()
    cl = parser.classify_layers(drawing)
    return [{"id": uuid4().hex[:12], "layer": e.layer, "points": e.points, "closed": e.closed, "thickness": 120}
            for e in cl["walls"] if len(e.points) >= 2]


def extract_doors_from_cad(drawing: CADDrawing, parser=None):
    if parser is None: parser = DXFParser()
    cl = parser.classify_layers(drawing)
    return [{"id": uuid4().hex[:12], "layer": e.layer, "position": (e.points[0] if e.points else (0, 0)), "width": 900}
            for e in cl["doors"]]


def extract_rooms_from_cad(drawing: CADDrawing, parser=None):
    if parser is None: parser = DXFParser()
    cl = parser.classify_layers(drawing)
    rooms = [{"id": uuid4().hex[:12], "label": e.text, "position": (e.points[0] if e.points else (0, 0))}
             for e in cl["text"] if e.text]
    for e in cl["rooms"]:
        if e.closed and len(e.points) >= 3:
            rooms.append({"id": uuid4().hex[:12], "label": e.layer, "polygon": e.points})
    return rooms
