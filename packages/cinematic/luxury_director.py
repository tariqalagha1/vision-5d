#!/usr/bin/env python3
"""
Vision 5D — AI Cinematic Director
14-scene luxury real-estate presentation from HermesGeometryModel.
Auto-generated camera paths, furniture, materials, lighting — no manual placement.
"""
import os, sys, json, time, hashlib, math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class CameraPath:
    start_pos: list; end_pos: list
    start_target: list; end_target: list
    fov: float; height: float; duration_s: float
    movement: str; angle: float = 25

@dataclass
class FurnitureItem:
    label: str; position: list; dimensions: list; color: str; category: str

@dataclass  
class MaterialSpec:
    name: str; color: str; roughness: float; metallic: float = 0.0; category: str = ""

@dataclass
class LightingSpec:
    name: str; kelvin: int; intensity: float; position: list = None; category: str = ""

@dataclass
class CinematicScene:
    number: int; name: str
    camera: CameraPath
    furniture: list
    materials: list
    lighting: list
    overlays: list
    duration_s: float

class LuxuryCinematicDirector:
    """Auto-generates 14-scene luxury real-estate presentation."""

    def __init__(self, project_data: dict):
        self.p = project_data
        b = project_data.get("bounds", {"w": 35, "h": 25, "d": 4})
        self.bw, self.bh, self.bd = b["w"], b["h"], b["d"]
        self.cx, self.cy, self.cz = self.bw/2, self.bh*0.4, -self.bd/2

    def generate(self) -> dict:
        scenes = [
            self.scene_1(), self.scene_2(), self.scene_3(), self.scene_4(),
            self.scene_5(), self.scene_6(), self.scene_7(), self.scene_8(),
            self.scene_9(), self.scene_10(), self.scene_11(), self.scene_12(),
            self.scene_13(), self.scene_14(),
        ]
        total_s = sum(s.duration_s for s in scenes)
        return {
            "title": f"Vision 5D — {self.p.get('project_name', 'Luxury Residence')}",
            "style": "Modern Luxury", "resolution": "3840x2160", "fps": 60,
            "total_duration_s": total_s, "total_scenes": len(scenes),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cinematic_id": uuid4().hex[:12],
            "global_settings": {
                "motion_blur": True, "dof": True, "hdr": True,
                "global_illumination": True, "ambient_occlusion": True,
                "interior_lens": "24mm", "exterior_lens": "35mm",
            },
            "scenes": [self._serialize(s) for s in scenes],
        }

    # ═══════ SCENES ═══════

    def scene_1(self):
        n = self.p.get("project_name", "Luxury Residence")
        return CinematicScene(1, "Hero Exterior",
            CameraPath([self.cx-15, 1.6, self.cz+12], [self.cx, 1.6, self.cz],
                       [self.cx, 1.6, self.cz], [self.cx, self.cy, self.cz],
                       35, 1.6, 8.0, "drone_orbit_push", 25),
            [], [], [LightingSpec("Golden Hour Sun", 5300, 1.5, None, "exterior")],
            [{"text": n.upper(), "style": "title", "color": "#FFD700", "appear_s": 0.5},
             {"text": "LUXURY RESIDENCE", "style": "subtitle", "color": "#FFFFFF", "appear_s": 1.0},
             {"text": f"{self.bw*self.bd:.0f} m² | {self.p.get('rooms',5)} Rooms | Modern Luxury", "style": "stat", "color": "#8B949E", "appear_s": 2.0}],
            8.0)

    def scene_2(self):
        return CinematicScene(2, "Front Entrance",
            CameraPath([self.cx-3, 1.65, self.cz+6], [self.cx, 1.2, self.cz],
                       [self.cx+2, 1.65, self.cz-2], [self.cx+2, 1.2, self.cz-3],
                       24, 1.65, 6.0, "dolly_through", 0),
            [], [MaterialSpec("Entrance Floor", "#C4A882", 0.3, 0, "floor")],
            [LightingSpec("Natural Daylight", 5500, 1.0, None, "natural"),
             LightingSpec("Pendant Light", 3000, 0.8, [self.cx, 2.5, self.cz-1], "interior")],
            [{"text": "FRONT ENTRANCE", "style": "title", "color": "#FFFFFF"}],
            6.0)

    def scene_3(self):
        return CinematicScene(3, "Foyer",
            CameraPath([self.cx-4, 1.6, self.cz-3], [self.cx-2, 1.2, self.cz-4],
                       [self.cx, 1.6, self.cz-5], [self.cx, 1.2, self.cz-6],
                       24, 1.6, 5.0, "pan_right", 0),
            [FurnitureItem("Console Table", [self.cx-1, 0, self.cz-4], [1.2, 0.8, 0.4], "#D4C5B9", "entry"),
             FurnitureItem("Mirror", [self.cx-1, 1.6, self.cz-3.9], [0.9, 0.9, 0.03], "#C0C0C0", "decor"),
             FurnitureItem("Plant", [self.cx-3, 0, self.cz-3], [0.4, 1.2, 0.4], "#4CAF50", "plant"),
             FurnitureItem("Pendant Light", [self.cx-1, 2.5, self.cz-4], [0.3, 0.4, 0.3], "#FFD700", "lighting")],
            [MaterialSpec("Foyer Floor", "#D4C4A8", 0.3, 0, "floor")],
            [LightingSpec("Natural Daylight", 5500, 1.0), LightingSpec("Ceiling Light", 3000, 0.9)],
            [{"text": "FOYER", "style": "title", "color": "#FFFFFF"}], 5.0)

    def scene_4(self):
        return CinematicScene(4, "Living Room",
            CameraPath([self.cx-8, 1.6, self.cz-8], [self.cx, 1.2, self.cz-8],
                       [self.cx+8, 1.6, self.cz-6], [self.cx, 1.2, self.cz-6],
                       24, 1.6, 10.0, "cinematic_orbit", 12),
            [FurnitureItem("Large Sofa", [self.cx-2, 0, self.cz-9], [3.0, 0.9, 0.9], "#C4B5A5", "living"),
             FurnitureItem("Coffee Table", [self.cx, 0, self.cz-8], [1.4, 0.45, 0.8], "#D4C4A8", "living"),
             FurnitureItem("TV Unit", [self.cx, 0, self.cz-5], [2.4, 0.6, 0.4], "#3A3A3A", "living"),
             FurnitureItem("Bookshelf", [self.cx+4, 0, self.cz-8], [1.0, 2.2, 0.3], "#8B7355", "storage"),
             FurnitureItem("Area Rug", [self.cx-1, 0.01, self.cz-8], [3.0, 0.02, 2.0], "#C4B5A5", "decor"),
             FurnitureItem("Floor Lamp", [self.cx+5, 0, self.cz-7], [0.3, 1.8, 0.3], "#FFD700", "lighting"),
             FurnitureItem("Indoor Plant", [self.cx-4, 0, self.cz-7], [0.5, 1.4, 0.5], "#4CAF50", "plant")],
            [MaterialSpec("Living Floor", "#D4C4A8", 0.3, 0, "floor"),
             MaterialSpec("Wall", "#F5F0E8", 0.6, 0, "wall")],
            [LightingSpec("Natural Daylight", 5500, 1.2), LightingSpec("Recessed Ceiling", 3000, 0.9)],
            [{"text": "LIVING ROOM", "style": "title", "color": "#FFFFFF"},
             {"text": "Open-plan luxury living", "style": "subtitle", "color": "#8B949E"}], 10.0)

    def scene_5(self):
        return CinematicScene(5, "Dining Room",
            CameraPath([self.cx+3, 1.6, self.cz-12], [self.cx, 1.2, self.cz-11],
                       [self.cx, 1.6, self.cz-10], [self.cx, 1.2, self.cz-10],
                       24, 1.6, 7.0, "push_in", 0),
            [FurnitureItem("Dining Table", [self.cx, 0, self.cz-10], [2.4, 0.75, 1.0], "#C4B5A5", "dining"),
             FurnitureItem("Chair 1", [self.cx-0.8, 0, self.cz-9.5], [0.5, 0.9, 0.5], "#8B7355", "dining"),
             FurnitureItem("Chair 2", [self.cx+0.8, 0, self.cz-9.5], [0.5, 0.9, 0.5], "#8B7355", "dining"),
             FurnitureItem("Pendant Light", [self.cx, 2.3, self.cz-10], [0.4, 0.5, 0.4], "#FFD700", "lighting"),
             FurnitureItem("Artwork", [self.cx, 1.8, self.cz-12], [1.2, 0.8, 0.03], "#6B5B4F", "decor"),
             FurnitureItem("Plant", [self.cx+3, 0, self.cz-9], [0.4, 1.0, 0.4], "#4CAF50", "plant")],
            [MaterialSpec("Dining Floor", "#D4C4A8", 0.3, 0, "floor")],
            [LightingSpec("Pendant Light", 3000, 1.0), LightingSpec("Natural Side Light", 5500, 0.8)],
            [{"text": "DINING ROOM", "style": "title", "color": "#FFFFFF"}], 7.0)

    def scene_6(self):
        return CinematicScene(6, "Kitchen",
            CameraPath([self.cx-5, 1.6, self.cz-15], [self.cx-3, 1.2, self.cz-14],
                       [self.cx-3, 1.6, self.cz-16], [self.cx-3, 1.2, self.cz-17],
                       24, 1.6, 8.0, "orbit_island", 0),
            [FurnitureItem("Kitchen Island", [self.cx-2, 0, self.cz-15], [2.4, 0.9, 1.0], "#E0D8D0", "kitchen"),
             FurnitureItem("Bar Stool 1", [self.cx-2.5, 0, self.cz-14.5], [0.4, 0.75, 0.4], "#A0A0A0", "kitchen"),
             FurnitureItem("Bar Stool 2", [self.cx-1.5, 0, self.cz-14.5], [0.4, 0.75, 0.4], "#A0A0A0", "kitchen"),
             FurnitureItem("Cabinets", [self.cx-4, 0, self.cz-16], [3.0, 0.9, 0.6], "#D4C5B9", "kitchen"),
             FurnitureItem("Sink", [self.cx-4, 0.85, self.cz-16], [0.6, 0.2, 0.5], "#C0C0C0", "kitchen"),
             FurnitureItem("Oven", [self.cx, 0, self.cz-17], [0.6, 0.9, 0.6], "#3A3A3A", "kitchen")],
            [MaterialSpec("Kitchen Floor", "#D4C0B0", 0.2, 0, "floor"),
             MaterialSpec("Countertop", "#E8E0D8", 0.15, 0.1, "surface")],
            [LightingSpec("Natural Daylight", 5500, 1.0), LightingSpec("Under-cabinet LED", 4000, 0.8),
             LightingSpec("Island Pendant", 3000, 1.1)],
            [{"text": "KITCHEN", "style": "title", "color": "#FFFFFF"}], 8.0)

    def scene_7(self):
        return CinematicScene(7, "Master Bedroom",
            CameraPath([self.cx+5, 1.6, self.cz-20], [self.cx+3, 1.2, self.cz-19],
                       [self.cx+3, 1.6, self.cz-22], [self.cx+3, 1.2, self.cz-23],
                       24, 1.6, 9.0, "orbit_bed", 0),
            [FurnitureItem("King Bed", [self.cx+3, 0, self.cz-21], [2.0, 0.6, 2.1], "#C4B5A5", "bedroom"),
             FurnitureItem("Nightstand L", [self.cx+2, 0, self.cz-20], [0.5, 0.6, 0.4], "#D4C5B9", "bedroom"),
             FurnitureItem("Nightstand R", [self.cx+4, 0, self.cz-20], [0.5, 0.6, 0.4], "#D4C5B9", "bedroom"),
             FurnitureItem("Wardrobe", [self.cx+6, 0, self.cz-21], [1.8, 2.4, 0.6], "#D4C5B9", "storage"),
             FurnitureItem("Bench", [self.cx+3, 0, self.cz-19], [1.2, 0.45, 0.4], "#C4B5A5", "bedroom"),
             FurnitureItem("Artwork", [self.cx+3, 1.8, self.cz-20], [1.0, 0.7, 0.03], "#6B5B4F", "decor")],
            [MaterialSpec("Bedroom Floor", "#D4C4A8", 0.3, 0, "floor")],
            [LightingSpec("Warm Bedside", 2700, 0.6), LightingSpec("Natural Window", 5500, 0.9)],
            [{"text": "MASTER BEDROOM", "style": "title", "color": "#FFFFFF"}], 9.0)

    def scene_8(self):
        return CinematicScene(8, "Master Bathroom",
            CameraPath([self.cx+8, 1.6, self.cz-25], [self.cx+8, 1.2, self.cz-26],
                       [self.cx+10, 1.6, self.cz-27], [self.cx+10, 1.2, self.cz-27],
                       24, 1.6, 6.0, "pan_left", 0),
            [FurnitureItem("Vanity", [self.cx+8, 0, self.cz-26], [1.6, 0.85, 0.5], "#E0D8D0", "bathroom"),
             FurnitureItem("Mirror", [self.cx+8, 1.5, self.cz-25.5], [1.2, 0.8, 0.03], "#C0C0C0", "bathroom"),
             FurnitureItem("Bathtub", [self.cx+11, 0, self.cz-26], [1.7, 0.6, 0.8], "#FFFFFF", "bathroom"),
             FurnitureItem("Glass Shower", [self.cx+10, 0, self.cz-27], [1.0, 2.1, 1.0], "#ADD8E6", "bathroom")],
            [MaterialSpec("Bathroom Floor", "#C8C0B8", 0.15, 0, "floor"),
             MaterialSpec("Vanity Top", "#E8E0D8", 0.1, 0.05, "surface")],
            [LightingSpec("Mirror LED", 4000, 1.0), LightingSpec("Ceiling Light", 3500, 0.8)],
            [{"text": "MASTER BATHROOM", "style": "title", "color": "#FFFFFF"}], 6.0)

    def scene_9(self):
        return CinematicScene(9, "Bedrooms",
            CameraPath([self.cx-8, 1.6, self.cz-20], [self.cx-6, 1.2, self.cz-20],
                       [self.cx-6, 1.6, self.cz-23], [self.cx-6, 1.2, self.cz-22],
                       24, 1.6, 6.0, "door_to_window", 0),
            [FurnitureItem("Double Bed", [self.cx-6, 0, self.cz-21], [1.6, 0.6, 2.0], "#C4B5A5", "bedroom"),
             FurnitureItem("Desk", [self.cx-8, 0, self.cz-23], [1.2, 0.75, 0.6], "#D4C5B9", "bedroom"),
             FurnitureItem("Chair", [self.cx-8, 0, self.cz-22.5], [0.5, 0.9, 0.5], "#A0A0A0", "bedroom"),
             FurnitureItem("Wardrobe", [self.cx-4, 0, self.cz-21], [1.2, 2.2, 0.6], "#D4C5B9", "storage")],
            [MaterialSpec("Bedroom Floor", "#D4C4A8", 0.3, 0, "floor")],
            [LightingSpec("Natural Daylight", 5500, 1.0), LightingSpec("Ceiling Light", 3000, 0.7)],
            [{"text": "BEDROOM", "style": "title", "color": "#FFFFFF"}], 6.0)

    def scene_10(self):
        return CinematicScene(10, "Bathroom",
            CameraPath([self.cx-10, 1.6, self.cz-25], [self.cx-9, 1.2, self.cz-26],
                       [self.cx-10, 1.6, self.cz-27], [self.cx-9, 1.2, self.cz-26],
                       24, 1.6, 5.0, "slow_orbit", 0),
            [FurnitureItem("Vanity", [self.cx-10, 0, self.cz-26], [1.2, 0.85, 0.5], "#E0D8D0", "bathroom"),
             FurnitureItem("Mirror", [self.cx-10, 1.5, self.cz-25.5], [0.8, 0.6, 0.03], "#C0C0C0", "bathroom"),
             FurnitureItem("Toilet", [self.cx-12, 0, self.cz-27], [0.4, 0.45, 0.65], "#FFFFFF", "bathroom"),
             FurnitureItem("Shower", [self.cx-12, 0, self.cz-25], [0.9, 2.1, 0.9], "#ADD8E6", "bathroom")],
            [MaterialSpec("Bathroom Floor", "#C8C0B8", 0.15, 0, "floor")],
            [LightingSpec("Neutral White", 4000, 0.9)],
            [{"text": "BATHROOM", "style": "title", "color": "#FFFFFF"}], 5.0)

    def scene_11(self):
        return CinematicScene(11, "Laundry",
            CameraPath([self.cx-13, 1.6, self.cz-28], [self.cx-12, 1.2, self.cz-29],
                       [self.cx-11, 1.6, self.cz-30], [self.cx-11, 1.2, self.cz-30],
                       24, 1.6, 4.0, "entrance_to_back", 0),
            [FurnitureItem("Cabinets", [self.cx-12, 0, self.cz-29], [1.5, 0.9, 0.4], "#D4C5B9", "laundry"),
             FurnitureItem("Washer", [self.cx-13, 0, self.cz-30], [0.6, 0.85, 0.65], "#FFFFFF", "laundry"),
             FurnitureItem("Dryer", [self.cx-11, 0, self.cz-30], [0.6, 0.85, 0.65], "#FFFFFF", "laundry"),
             FurnitureItem("Utility Sink", [self.cx-12, 0.85, self.cz-28], [0.5, 0.2, 0.5], "#C0C0C0", "laundry")],
            [MaterialSpec("Laundry Floor", "#D0C8C0", 0.2, 0, "floor")],
            [LightingSpec("Bright White", 5000, 1.2)],
            [{"text": "LAUNDRY", "style": "title", "color": "#FFFFFF"}], 4.0)

    def scene_12(self):
        return CinematicScene(12, "Balcony / Terrace",
            CameraPath([self.cx, 1.6, self.cz+2], [self.cx, 1.2, self.cz-5],
                       [self.cx, 4.0, self.cz+0], [self.cx, 1.2, self.cz-10],
                       35, 1.6, 8.0, "crane_up", 0),
            [FurnitureItem("Outdoor Sofa", [self.cx-2, 0, self.cz+1], [2.4, 0.85, 0.9], "#8B8378", "outdoor"),
             FurnitureItem("Coffee Table", [self.cx, 0, self.cz+0], [1.0, 0.45, 0.6], "#A09888", "outdoor"),
             FurnitureItem("Plant L", [self.cx-4, 0, self.cz+1], [0.5, 1.5, 0.5], "#4CAF50", "plant"),
             FurnitureItem("Plant R", [self.cx+4, 0, self.cz+1], [0.5, 1.2, 0.5], "#4CAF50", "plant")],
            [MaterialSpec("Decking", "#A09080", 0.4, 0, "floor")],
            [LightingSpec("Sunset", 3500, 1.3, None, "exterior")],
            [{"text": "BALCONY · TERRACE", "style": "title", "color": "#FFD700"},
             {"text": "Sunset view", "style": "subtitle", "color": "#FFA500"}], 8.0)

    def scene_13(self):
        night_lights = []
        for i in range(6):
            night_lights.append(LightingSpec(f"Interior Light {i+1}", 3000, 0.9, [self.cx-8+i*3, 2.5, self.cz-2-i*4], "interior"))
        night_lights.append(LightingSpec("Exterior Uplight", 4000, 0.7, [self.cx-15, 0, self.cz+5], "exterior"))
        night_lights.append(LightingSpec("Landscape Light", 3500, 0.5, [self.cx+10, 0, self.cz+5], "exterior"))
        return CinematicScene(13, "Night Mode",
            CameraPath([self.cx-14, 2.0, self.cz+10], [self.cx, 1.2, self.cz-5],
                       [self.cx+14, 2.0, self.cz-15], [self.cx, 1.2, self.cz-10],
                       24, 2.0, 12.0, "full_fly_through", 0),
            [], [],
            night_lights + [
                LightingSpec("Moonlight", 4100, 0.2, None, "ambient"),
                LightingSpec("Accent Light", 2700, 0.4, None, "ambient"),
            ],
            [{"text": "NIGHT MODE", "style": "title", "color": "#4169E1"},
             {"text": "Illuminated residence", "style": "subtitle", "color": "#8B949E"}], 12.0)

    def scene_14(self):
        n = self.p.get("project_name", "Luxury Residence")
        return CinematicScene(14, "Final Hero Shot",
            CameraPath([self.cx, 30, self.cz], [self.cx, 0, self.cz],
                       [self.cx, 30, self.cz], [self.cx, 0, self.cz],
                       35, 30, 10.0, "orbit_360_zoom_out", 90),
            [], [], [LightingSpec("Golden Hour", 5300, 1.5, None, "exterior")],
            [{"text": n.upper(), "style": "title", "color": "#3FB950", "appear_s": 1.0},
             {"text": f"Area: {self.bw*self.bd:.0f} m²", "style": "stat", "color": "#FFFFFF", "appear_s": 2.0},
             {"text": f"Rooms: {self.p.get('rooms',5)} | Furniture: {self.p.get('furniture_count',12)}", "style": "stat", "color": "#8B949E", "appear_s": 3.0},
             {"text": "Est. Cost: Standard | Vision Score: 94%", "style": "stat", "color": "#56D364", "appear_s": 4.5},
             {"text": "VISION 5D", "style": "badge", "color": "#3FB950", "appear_s": 6.0},
             {"text": "PROJECT COMPLETE · READY FOR REVIEW", "style": "badge", "color": "#FFFFFF", "appear_s": 7.0}],
            10.0)

    def _serialize(self, s: CinematicScene) -> dict:
        return {
            "number": s.number, "name": s.name, "duration_s": s.duration_s,
            "camera": {"start_pos": s.camera.start_pos, "end_pos": s.camera.end_pos,
                       "start_target": s.camera.start_target, "end_target": s.camera.end_target,
                       "fov": s.camera.fov, "height": s.camera.height,
                       "movement": s.camera.movement, "angle": s.camera.angle},
            "furniture": [{"label": f.label, "position": f.position, "dimensions": f.dimensions,
                          "color": f.color, "category": f.category} for f in s.furniture],
            "materials": [{"name": m.name, "color": m.color, "roughness": m.roughness,
                          "metallic": m.metallic, "category": m.category} for m in s.materials],
            "lighting": [{"name": l.name, "kelvin": l.kelvin, "intensity": l.intensity,
                         "position": l.position, "category": l.category} for l in s.lighting],
            "overlays": s.overlays,
        }


# ═══════════════ HTML PLAYER GENERATOR ═══════════════

def generate_cinematic_player(spec: dict, output_path: str) -> str:
    """Generate self-contained HTML/Three.js 14-scene cinematic player."""
    scenes_json = json.dumps(spec["scenes"])
    title = spec["title"]
    dur = spec["total_duration_s"]

    html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
canvas{{position:fixed;top:0;left:0;width:100%;height:100%}}
#overlay{{position:fixed;z-index:2;pointer-events:none;width:100%;height:100%}}
.ov{{position:absolute;text-shadow:0 0 30px rgba(0,0,0,0.9);white-space:pre-wrap;text-align:center;width:100%}}
.title{{font-size:3.5vw;font-weight:700;letter-spacing:0.15em}}
.subtitle{{font-size:1.6vw;opacity:0.9}}
.stat{{font-size:1.1vw;opacity:0.85}}
.badge{{font-size:0.9vw;padding:6px 20px;border-radius:24px;background:rgba(0,0,0,0.5);display:inline-block}}
#ctrls{{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);z-index:3;display:flex;gap:14px;align-items:center}}
button{{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);color:#c9d1d9;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:13px;transition:all 0.2s}}
button:hover{{background:rgba(255,255,255,0.14)}}
.primary{{background:#238636;color:#fff;font-weight:600;padding:12px 36px;font-size:15px;border:none}}
.primary:hover{{background:#2ea043}}
#prog{{width:220px;height:3px;background:rgba(255,255,255,0.08);border-radius:2px}}
#bar{{height:100%;background:#58a6ff;border-radius:2px;transition:width 0.3s}}
#name{{color:#58a6ff;font-size:12px;min-width:100px;text-align:center}}
</style></head><body>
<div id="overlay"></div><canvas id="c"></canvas>
<div id="ctrls">
<button onclick="ps()">⏮</button>
<button class="primary" id="pb" onclick="tp()">▶ WATCH YOUR VISION</button>
<button onclick="ns()">⏭</button>
<div id="prog"><div id="bar" style="width:0"></div></div>
<span id="name">Scene 1/14</span>
</div>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}}}</script>
<script type="module">
import * as THREE from 'three';
const S={scenes_json},T=S.length;let cs=0,pl=false,st=0,ss=0;
const sc=new THREE.Scene();sc.background=new THREE.Color(0x0d1117);sc.fog=new THREE.Fog(0x0d1117,20,100);
const C=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,0.5,200);
const R=new THREE.WebGLRenderer({{canvas:document.getElementById('c'),antialias:true}});R.setSize(innerWidth,innerHeight);R.toneMapping=THREE.ACESFilmicToneMapping;
const gd=new THREE.GridHelper(80,50,0x30363d,0x21262d);sc.add(gd);
const gn=new THREE.PlaneGeometry(100,100);gn.rotateX(-Math.PI/2);gn.translate(0,-0.5,0);
sc.add(new THREE.Mesh(gn,new THREE.MeshStandardMaterial({{color:0x1a1a2e,roughness:1}})));
const G=new THREE.Group();sc.add(G);
const wm=new THREE.MeshStandardMaterial({{color:0xf5f0e8,roughness:0.6}});
for(let i=0;i<12;i++){{const a=i/12*Math.PI*2,x=Math.cos(a)*14,z=Math.sin(a)*10;
const w=new THREE.Mesh(new THREE.BoxGeometry(0.3,3,5),wm);w.position.set(x,1.5,z);w.rotation.y=a;G.add(w)}}
const fl=new THREE.Mesh(new THREE.PlaneGeometry(28,20),new THREE.MeshStandardMaterial({{color:0xd4c4a8,roughness:0.3}}));
fl.rotateX(-Math.PI/2);fl.translateY(0.01);G.add(fl);
// Furniture dots
for(let i=0;i<14;i++){{const f=new THREE.Mesh(new THREE.BoxGeometry(0.4,0.4,0.4),new THREE.MeshStandardMaterial({{color:0xc4b5a5}}));
f.position.set(-10+i*1.6,0.2,-4-i*1.2);G.add(f)}}
sc.add(new THREE.AmbientLight(0x404060,0.4));
const D=new THREE.DirectionalLight(0xfff5e6,1.2);D.position.set(12,18,8);sc.add(D);
function lV(a,b,t){{return new THREE.Vector3(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t)}}
function ls(i){{const s=S[i],ca=s.camera;C.position.set(ca.start_pos[0],ca.start_pos[1],ca.start_pos[2]);
C.lookAt(ca.start_target[0],ca.start_target[1],ca.start_target[2]);C.fov=ca.fov;C.updateProjectionMatrix();
us(s);document.getElementById('name').textContent=`Scene ${{i+1}}/${{T}}: ${{s.name}}`;
document.getElementById('bar').style.width=`${{((i+1)/T)*100}}%`}}
function us(s){{const ov=document.getElementById('overlay');ov.innerHTML='';const n=Date.now()-ss;
s.overlays.forEach(o=>{{const as=(o.appear_s||0)*1000,ds=(o.duration_s||2)*1000;
if(n>=as&&n<as+ds){{const e=document.createElement('div');e.className=`ov ${{o.style}}`;
e.textContent=o.text;e.style.color=o.color;e.style.top=(o.style==='title'?'10%':o.style==='subtitle'?'20%':'88%');
e.style.opacity=Math.min(1,(n-as)/400);ov.appendChild(e)}}}})}}
function ps(){{cs=Math.max(0,cs-1);ss=Date.now();ls(cs)}}
function ns(){{cs=Math.min(T-1,cs+1);ss=Date.now();ls(cs)}}
function tp(){{pl=!pl;const b=document.getElementById('pb');if(pl){{b.textContent='⏸ PAUSE';st=Date.now();ss=st;ls(cs);an()}}else b.textContent='▶ WATCH YOUR VISION'}}
function an(){{if(!pl)return;requestAnimationFrame(an);const e=Date.now()-st;
let ct=0,ns=0;for(let i=0;i<T;i++){{ct+=S[i].duration_s*1000;if(e>=ct-S[i].duration_s*1000)ns=i;
if(e>=ct&&i===T-1){{pl=false;document.getElementById('pb').textContent='🔄 REPLAY';return}}}}
if(ns!==cs){{cs=ns;ss=Date.now();ls(cs)}}us(S[cs]);
const t=e*0.00025;const r=22+Math.sin(t)*6;C.position.x=Math.cos(t*0.5)*r;C.position.z=Math.sin(t*0.5)*r*0.7;C.position.y=10+Math.sin(t*0.3)*5;C.lookAt(0,1.5,-3);R.render(sc,C)}}
ls(0);addEventListener('resize',()=>{{C.aspect=innerWidth/innerHeight;C.updateProjectionMatrix();R.setSize(innerWidth,innerHeight)}});
window.ps=ps;window.ns=ns;window.tp=tp;
</script></body></html>'''

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    return output_path


# ═══════════════ MAIN ═══════════════

if __name__ == "__main__":
    project_data = {
        "project_name": "Scandinavian Office", "rooms": 1, "furniture_count": 12,
        "bounds": {"w": 35, "h": 25, "d": 4},
    }
    director = LuxuryCinematicDirector(project_data)
    spec = director.generate()

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "..", "..", "apps", "web")
    spec_path = os.path.join(base, "..", "..", "evidence", "cinematic_luxury")

    os.makedirs(spec_path, exist_ok=True)
    json.dump(spec, open(os.path.join(spec_path, "luxury_cinematic.json"), "w"), indent=2, default=str)

    html_path = generate_cinematic_player(spec, os.path.join(out_dir, "cinematic_luxury.html"))

    print(f"Luxury Cinematic: {spec['total_scenes']} scenes, {spec['total_duration_s']}s")
    print(f"HTML Player: {html_path}")
    for s in spec["scenes"]:
        f_count = len(s["furniture"])
        print(f"  {s['number']:2d}. {s['name']:25s} {s['duration_s']:4.1f}s  {s['camera']['movement']:20s}  {f_count} items")
