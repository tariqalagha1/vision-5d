#!/usr/bin/env python3
"""
Vision 5D — Realistic Architectural DXF Generator
Produces a professional 2-bedroom apartment floor plan in DXF format.
Walls on A-WALL layer, doors on A-DOOR, windows on A-WINDOW,
dimensions on A-DIM, text on A-TEXT.
"""
import math, os


def generate_apartment_dxf(output_path: str = None) -> str:
    """Generate a realistic 2-bedroom apartment DXF and return the content."""
    lines = []
    L = lines.append

    # ── DXF Header ──
    L("0"); L("SECTION")
    L("2"); L("HEADER")
    L("9"); L("$ACADVER"); L("1"); L("AC1021")
    L("9"); L("$INSUNITS"); L("70"); L("4")  # mm
    L("0"); L("ENDSEC")

    # ── Tables ──
    L("0"); L("SECTION"); L("2"); L("TABLES")
    L("0"); L("TABLE"); L("2"); L("LAYER"); L("70"); L("6")

    for name, color in [("A-WALL", 7), ("A-DOOR", 4), ("A-WINDOW", 5),
                         ("A-DIM", 2), ("A-TEXT", 3), ("A-ROOM", 8)]:
        L("0"); L("LAYER"); L("2"); L(name); L("70"); L("0"); L("62"); L(str(color)); L("6"); L("CONTINUOUS")

    L("0"); L("ENDTAB"); L("0"); L("ENDSEC")

    # ── Blocks (Door symbol) ──
    L("0"); L("SECTION"); L("2"); L("BLOCKS")
    L("0"); L("BLOCK"); L("8"); L("0"); L("2"); L("DOOR_SWING"); L("70"); L("0")
    L("10"); L("0"); L("20"); L("0"); L("30"); L("0")
    L("0"); L("ARC"); L("8"); L("0"); L("10"); L("0"); L("20"); L("0"); L("40"); L("900")
    L("50"); L("0"); L("51"); L("90")
    L("0"); L("LINE"); L("8"); L("0"); L("10"); L("0"); L("20"); L("0")
    L("11"); L("900"); L("21"); L("0")
    L("0"); L("ENDBLK")
    L("0"); L("ENDSEC")

    # ── Entities ──
    L("0"); L("SECTION"); L("2"); L("ENTITIES")

    # ==== EXTERIOR WALLS (12000 x 9000 mm apartment) ====
    # Layout: Living/Dining at bottom-left, Kitchen top-left, Bedroom1 bottom-right, Bedroom2 top-right, Bathroom center-right

    def wall_line(x1, y1, x2, y2, layer="A-WALL"):
        L("0"); L("LINE"); L("8"); L(layer)
        L("10"); L(str(x1)); L("20"); L(str(y1)); L("30"); L("0")
        L("11"); L(str(x2)); L("21"); L(str(y2)); L("31"); L("0")

    def wall_rect(x, y, w, h, layer="A-WALL"):
        wall_line(x, y, x+w, y, layer)
        wall_line(x+w, y, x+w, y+h, layer)
        wall_line(x+w, y+h, x, y+h, layer)
        wall_line(x, y+h, x, y, layer)

    # Exterior perimeter
    wall_rect(0, 0, 12000, 9000)

    # Interior partitions
    # Horizontal: separating front/back zones at y=4500
    wall_line(0, 4500, 4000, 4500)   # Left segment (kitchen side)
    # Door gap at 4000-5000
    wall_line(5000, 4500, 12000, 4500)  # Right segment

    # Vertical: separating left (living/kitchen) from right (bedrooms/bath) at x=8000
    wall_line(8000, 4500, 8000, 9000)  # Top half
    wall_line(8000, 0, 8000, 3500)     # Bottom half
    # Door gap at 3500-4500

    # Kitchen partition (x=0 to x=4000, y=4500 to y=9000 → split kitchen+bath)
    wall_line(4000, 4500, 4000, 6500)
    wall_line(4000, 7500, 4000, 9000)
    # Door gap at 6500-7500

    # Bathroom at x=4000-8000, y=4500-9000
    wall_line(4000, 6500, 8000, 6500)  # Bathroom back wall (horizontal)
    # Open doorway at right

    # Bedroom 2 partition (top-right: x=8000-12000, y=4500-9000)
    wall_line(8000, 7000, 12000, 7000)  # Split Bed2 from Bath

    # ==== DOORS ====
    def door_insert(x, y, angle=0):
        L("0"); L("INSERT"); L("8"); L("A-DOOR")
        L("2"); L("DOOR_SWING")
        L("10"); L(str(x)); L("20"); L(str(y)); L("30"); L("0")
        L("41"); L("1.0"); L("42"); L("1.0"); L("43"); L("1.0")
        L("50"); L(str(angle))

    # Entry door (bottom center-left)
    door_insert(3000, 0, 0)

    # Living→Hall door
    door_insert(4000, 4500, 90)

    # Kitchen door
    door_insert(4000, 6500, 90)

    # Bedroom 1 door (bottom-right)
    door_insert(8000, 3500, 90)

    # Bedroom 2 door (top-right)
    door_insert(9000, 4500, 0)

    # Bathroom door
    door_insert(7000, 6500, 0)

    # ==== WINDOWS ====
    def window_line(x1, y1, x2, y2):
        L("0"); L("LINE"); L("8"); L("A-WINDOW")
        L("10"); L(str(x1)); L("20"); L(str(y1)); L("30"); L("0")
        L("11"); L(str(x2)); L("21"); L(str(y2)); L("31"); L("0")

    # Living room window (bottom, left side)
    window_line(2000, 0, 3000, 0)
    # Living room window (left side)
    window_line(0, 1500, 0, 2500)
    # Kitchen window (left side)
    window_line(0, 5500, 0, 7000)
    # Bedroom 1 window (bottom)
    window_line(9000, 0, 10500, 0)
    # Bedroom 2 window (right)
    window_line(12000, 5500, 12000, 6500)
    # Bathroom window (top)
    window_line(5500, 9000, 6500, 9000)

    # ==== DIMENSIONS ====
    def dim_line(y, label):
        L("0"); L("TEXT"); L("8"); L("A-DIM")
        L("10"); L("6000"); L("20"); L(str(y)); L("30"); L("0")
        L("40"); L("250"); L("1"); L(label); L("7"); L("STANDARD")

    dim_line(9200, "12000")
    dim_line(9400, "9000")
    L("0"); L("TEXT"); L("8"); L("A-DIM"); L("10"); L("12200"); L("20"); L("4500"); L("30"); L("0")
    L("40"); L("200"); L("1"); L("9000"); L("7"); L("STANDARD")

    # ==== ROOM LABELS ====
    def room_text(x, y, label, layer="A-TEXT"):
        L("0"); L("TEXT"); L("8"); L(layer)
        L("10"); L(str(x)); L("20"); L(str(y)); L("30"); L("0")
        L("40"); L("350"); L("1"); L(label); L("7"); L("STANDARD")

    room_text(4000, 2500, "LIVING ROOM")
    room_text(2000, 6500, "KITCHEN")
    room_text(10000, 7500, "BEDROOM 2")
    room_text(10000, 2000, "BEDROOM 1")
    room_text(6000, 8000, "BATHROOM")

    # ==== ROOM HATCH (A-ROOM layer, polylines) ====
    def room_polyline(points, layer="A-ROOM"):
        L("0"); L("LWPOLYLINE"); L("8"); L(layer)
        L("90"); L(str(len(points))); L("70"); L("1")  # closed
        for px, py in points:
            L("10"); L(str(px)); L("20"); L(str(py)); L("30"); L("0")

    room_polyline([(50, 50), (7950, 50), (7950, 4450), (50, 4450)])  # Living
    room_polyline([(50, 4550), (3950, 4550), (3950, 6450), (50, 6450)])  # Kitchen
    room_polyline([(8050, 50), (11950, 50), (11950, 3450), (8050, 3450)])  # Bed1
    room_polyline([(8050, 7050), (11950, 7050), (11950, 8950), (8050, 8950)])  # Bed2
    room_polyline([(4050, 7050), (7950, 7050), (7950, 8950), (4050, 8950)])  # Bath

    L("0"); L("ENDSEC")
    L("0"); L("EOF")

    content = "\r\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)
        print(f"[CAD] Generated: {output_path} ({len(content)} bytes)")

    return content


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "test_data", "2bed_apartment.dxf")
    generate_apartment_dxf(path)
    print("2-bedroom apartment DXF generated successfully")
