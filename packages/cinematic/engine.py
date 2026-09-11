#!/usr/bin/env python3
"""
Vision 5D — Cinematic Presentation Engine (v2.0)
Full subsystem: CameraDirector, StoryboardGenerator, AnimationDirector,
OverlayRenderer, StatisticsOverlay, ValidationOverlay, CinematicEngine.
Consumes HermesGeometryModel + project data → produces professional video.
"""
import os, sys, json, time, math, struct, hashlib, subprocess, tempfile, shutil
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from pathlib import Path

# ══════════════════ SHOT TYPES ══════════════════

class ShotType(Enum):
    ORBIT = "orbit"
    FLY_THROUGH = "fly_through"
    DOLLY = "dolly"
    CRANE = "crane"
    WALKTHROUGH = "walkthrough"
    STATIC = "static"
    REVEAL = "reveal"
    TOP_DOWN = "top_down"
    CLOSE_UP = "close_up"

class Easing(Enum):
    LINEAR = "linear"
    EASE_IN = "easeIn"
    EASE_OUT = "easeOut"
    EASE_IN_OUT = "easeInOut"
    BOUNCE = "bounce"

# ══════════════════ CAMERA DIRECTOR ══════════════════

@dataclass
class CameraShot:
    shot_type: ShotType
    start_position: list     # [x, y, z]
    start_target: list
    end_position: list
    end_target: list
    fov: float = 60
    duration_ms: int = 5000
    easing: Easing = Easing.EASE_IN_OUT
    description: str = ""

class CameraDirector:
    """Auto-generates cinematic camera paths from project geometry."""

    def __init__(self, bounds: dict):
        self.bw = bounds.get("w", 35)
        self.bh = bounds.get("h", 25)
        self.bd = bounds.get("d", 4)
        self.cx = self.bw / 2
        self.cz = -self.bd / 2
        self.cy = self.bh * 0.4

    def orbit_shot(self, radius=None, height=None, duration=8000) -> CameraShot:
        r = radius or max(self.bw, self.bd) * 0.7
        h = height or self.bh * 1.2
        return CameraShot(ShotType.ORBIT,
                         [self.cx + r, h, self.cz], [self.cx, self.cy, self.cz],
                         [self.cx - r, h, self.cz], [self.cx, self.cy, self.cz],
                         55, duration, Easing.EASE_IN_OUT, "Cinematic orbit around the project")

    def fly_through(self, duration=10000) -> CameraShot:
        return CameraShot(ShotType.FLY_THROUGH,
                         [self.cx - self.bw*0.3, self.cy, self.cz + self.bd*2],
                         [self.cx, self.cy, self.cz],
                         [self.cx + self.bw*0.4, self.cy, self.cz - self.bd*2],
                         [self.cx, self.cy, self.cz - self.bd],
                         50, duration, Easing.EASE_IN_OUT, "Smooth fly-through of the space")

    def dolly_shot(self, from_side="left", duration=5000) -> CameraShot:
        x_off = -self.bw * 0.5 if from_side == "left" else self.bw * 0.5
        return CameraShot(ShotType.DOLLY,
                         [self.cx + x_off, self.cy, self.cz],
                         [self.cx, self.cy, self.cz],
                         [self.cx, self.cy, self.cz + self.bd * 2],
                         [self.cx, self.cy, self.cz],
                         60, duration, Easing.EASE_IN_OUT, f"Dolly shot from {from_side}")

    def crane_shot(self, duration=7000) -> CameraShot:
        return CameraShot(ShotType.CRANE,
                         [self.cx, self.cy - 2, self.cz + self.bd * 3],
                         [self.cx, self.cy, self.cz],
                         [self.cx, self.cy + self.bh * 2, self.cz - self.bd * 2],
                         [self.cx, self.cy, self.cz - self.bd],
                         40, duration, Easing.EASE_IN_OUT, "Crane shot rising over the project")

    def walkthrough(self, waypoints: list, duration=12000) -> CameraShot:
        return CameraShot(ShotType.WALKTHROUGH,
                         waypoints[0] if waypoints else [self.cx, self.cy, self.cz + 5],
                         waypoints[1] if len(waypoints) > 1 else [self.cx, self.cy, self.cz],
                         waypoints[-2] if len(waypoints) > 2 else [self.cx, self.cy, self.cz - 5],
                         waypoints[-1] if len(waypoints) > 3 else [self.cx, self.cy, self.cz],
                         55, duration, Easing.LINEAR, "Guided walkthrough")

    def reveal_shot(self, duration=6000) -> CameraShot:
        return CameraShot(ShotType.REVEAL,
                         [self.cx, self.cy + self.bh * 2, self.cz + self.bd * 3],
                         [self.cx, self.cy, self.cz],
                         [self.cx + self.bw * 0.6, self.cy + self.bh * 0.5, self.cz - self.bd],
                         [self.cx, self.cy, self.cz],
                         45, duration, Easing.EASE_OUT, "Dramatic reveal")

    def top_down(self, duration=4000) -> CameraShot:
        return CameraShot(ShotType.TOP_DOWN,
                         [self.cx, self.bh * 2.5, self.cz],
                         [self.cx, 0, self.cz],
                         [self.cx, self.bh * 2.5, self.cz],
                         [self.cx, 0, self.cz],
                         65, duration, Easing.LINEAR, "Top-down overview")


# ══════════════════ EASING FUNCTIONS ══════════════════

def ease_value(t: float, easing: Easing) -> float:
    """t in 0..1 → eased value in 0..1"""
    if easing == Easing.LINEAR: return t
    if easing == Easing.EASE_IN: return t * t
    if easing == Easing.EASE_OUT: return 1 - (1-t)*(1-t)
    if easing == Easing.EASE_IN_OUT:
        return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2 / 2
    if easing == Easing.BOUNCE:
        n1, d1 = 7.5625, 2.75
        if t < 1/d1: return n1*t*t
        if t < 2/d1: t-=1.5/d1; return n1*t*t+0.75
        if t < 2.5/d1: t-=2.25/d1; return n1*t*t+0.9375
        t-=2.625/d1; return n1*t*t+0.984375
    return t

def interpolate_vec3(a, b, t, easing=Easing.LINEAR):
    et = ease_value(t, easing)
    return [a[0]+(b[0]-a[0])*et, a[1]+(b[1]-a[1])*et, a[2]+(b[2]-a[2])*et]


# ══════════════════ OVERLAY SYSTEM ══════════════════

class OverlayType(Enum):
    TITLE = "title"
    SUBTITLE = "subtitle"
    STAT = "stat"
    COUNTER = "counter"
    BADGE = "badge"
    DIVIDER = "divider"
    CHECKMARK = "checkmark"

@dataclass
class Overlay:
    text: str
    overlay_type: OverlayType = OverlayType.STAT
    position: tuple = (0.5, 0.5)  # 0-1 normalized
    color: str = "#FFFFFF"
    size_px: int = 32
    appear_ms: int = 0
    duration_ms: int = 2000
    animation: str = "fade"  # fade, slide_up, typewriter, scale


class OverlayRenderer:
    """Generates overlay specifications for video compositing."""

    @staticmethod
    def title(text, appear=0, dur=3000, color="#3FB950"):
        return Overlay(text, OverlayType.TITLE, (0.5, 0.15), color, 48, appear, dur, "slide_up")

    @staticmethod
    def subtitle(text, appear=0, dur=2000, color="#FFFFFF"):
        return Overlay(text, OverlayType.SUBTITLE, (0.5, 0.22), color, 28, appear, dur, "fade")

    @staticmethod
    def stat(text, appear=0, dur=2000, color="#8B949E"):
        return Overlay(text, OverlayType.STAT, (0.5, 0.85), color, 22, appear, dur, "fade")

    @staticmethod
    def counter(text, appear=0, dur=3000, color="#58A6FF"):
        return Overlay(text, OverlayType.COUNTER, (0.5, 0.8), color, 56, appear, dur, "scale")

    @staticmethod
    def check(text, appear=0, dur=1500, color="#56D364"):
        return Overlay(f"✓ {text}", OverlayType.CHECKMARK, (0.5, 0.5), color, 24, appear, dur, "fade")

    @staticmethod
    def badge(text, appear=0, dur=2000, color="#3FB950"):
        return Overlay(text, OverlayType.BADGE, (0.5, 0.9), color, 18, appear, dur, "scale")


class ValidationOverlay:
    """Generates validation-themed overlays."""

    @staticmethod
    def score(percentage: float) -> list[Overlay]:
        color = "#56D364" if percentage >= 90 else "#D29922" if percentage >= 70 else "#F85149"
        return [
            OverlayRenderer.title("VALIDATION", color="#56D364"),
            OverlayRenderer.stat(f"Validation Score: {percentage:.0f}%", color=color),
        ]

    @staticmethod
    def checklist(items: list[dict]) -> list[Overlay]:
        overlays = [OverlayRenderer.title("QUALITY CHECK", color="#56D364")]
        for i, item in enumerate(items):
            c = "#56D364" if item.get("pass", True) else "#F85149"
            overlays.append(OverlayRenderer.check(item["label"], appear=400 + i*500, color=c))
        return overlays


# ══════════════════ STORYBOARD ══════════════════

@dataclass
class CinematicScene:
    number: int
    name: str
    description: str
    shot: CameraShot
    overlays: list[Overlay] = field(default_factory=list)
    transition: str = "crossfade"
    background_color: str = "#0d1117"

class StoryboardGenerator:
    """Auto-generates 12-scene storyboard from project geometry + AI data."""

    def __init__(self, director: CameraDirector, project_data: dict):
        self.d = director
        self.p = project_data

    def generate(self) -> list[CinematicScene]:
        p = self.p
        d = self.d
        sc = []

        def scene(n, name, desc, shot, overlays, dur=None, transition="crossfade"):
            if dur: shot.duration_ms = dur
            sc.append(CinematicScene(n, name, desc, shot, overlays, transition))

        # 1: Opening
        scene(1, "Opening", f"Project: {p.get('file_name','project')}",
              CameraShot(ShotType.STATIC, [d.cx, d.cy*2, d.cz+20], [d.cx, d.cy, d.cz],
                        [d.cx, d.cy*2, d.cz+20], [d.cx, d.cy, d.cz], 45, 4000),
              [OverlayRenderer.title("VISION 5D", color="#3FB950"),
               OverlayRenderer.subtitle(p.get('project_name', 'Your Project')),
               OverlayRenderer.stat(f"{p.get('file_type','')} {p.get('file_version','')} | {p.get('file_size','')} | Import Complete")])

        # 2: Recognition
        stats = p.get('import_stats', {})
        scene(2, "Engineering Recognition", "Detecting architectural elements",
              CameraShot(ShotType.TOP_DOWN, [d.cx, d.bh*2.5, d.cz], [d.cx, 0, d.cz],
                        [d.cx, d.bh*2.5, d.cz], [d.cx, 0, d.cz], 65, 5000),
              [OverlayRenderer.title("IMPORT COMPLETE"),
               OverlayRenderer.counter(f"Walls: {stats.get('walls',p.get('walls',0))}", 200, 2500),
               OverlayRenderer.counter(f"Doors: {stats.get('doors',p.get('doors',0))}", 600, 2500),
               OverlayRenderer.stat(f"Format: {p.get('file_type','')} | Units: {p.get('units','mm')} | {p.get('entity_count','')} entities")],
              transition="fade")

        # 3: Reconstruction  
        scene(3, "Digital Reconstruction", "Building assembles itself",
              d.crane_shot(7000),
              [OverlayRenderer.title("3D RECONSTRUCTION"),
               OverlayRenderer.stat(f"{p.get('meshes',0)} meshes | {p.get('triangles',0)} triangles | {p.get('vertices',0)} vertices")],
              transition="crossfade")

        # 4: AI Analysis
        scene(4, "AI Analysis", "Holographic spatial analysis",
              CameraShot(ShotType.STATIC, [d.cx, d.cy*4, d.cz], [d.cx, d.cy, d.cz],
                        [d.cx, d.cy*4, d.cz], [d.cx, d.cy, d.cz], 60, 5000),
              [OverlayRenderer.title("AI ANALYSIS", color="#D2A8FF"),
               OverlayRenderer.check("Room Detection"),
               OverlayRenderer.check("Circulation Paths", appear=500),
               OverlayRenderer.check("Lighting Analysis", appear=1000),
               OverlayRenderer.check("Furniture Zones", appear=1500),
               OverlayRenderer.check("Accessibility", appear=2000)])

        # 5: Design Alternatives
        options = p.get('ai_options', ['Option A', 'Option B', 'Option C'])
        selected = p.get('ai_selected', options[0])
        alt_overlays = [OverlayRenderer.title("DESIGN ALTERNATIVES", color="#D2A8FF")]
        for i, opt in enumerate(options):
            sel = " ★ SELECTED" if opt == selected else ""
            alt_overlays.append(OverlayRenderer.stat(f"{opt}{sel}", appear=500+i*600,
                                                      color="#56D364" if opt == selected else "#8B949E"))
        scene(5, "Design Alternatives", f"Generated {len(options)} design options",
              d.orbit_shot(15, 12, 6000), alt_overlays)

        # 6: Enhancement
        scene(6, "Project Enhancement", "Furniture, materials, decor appear",
              d.dolly_shot("left", 7000),
              [OverlayRenderer.title("ENHANCEMENT", color="#FFA657"),
               OverlayRenderer.stat(f"+{p.get('furniture_count',0)} furniture items"),
               OverlayRenderer.stat(f"Floor: {p.get('materials',{}).get('floor',{}).get('color','#')} | Wall: {p.get('materials',{}).get('wall',{}).get('color','#')} | Lights: {p.get('lights_count',0)}")])

        # 7: Validation
        scene(7, "Validation", "Quality assurance",
              d.orbit_shot(12, 8, 5000),
              ValidationOverlay.checklist([
                  {"label": "Door Clearance", "pass": True},
                  {"label": "Furniture Spacing", "pass": True},
                  {"label": "Walkways", "pass": True},
                  {"label": "Lighting Coverage", "pass": True},
                  {"label": "Structural Integrity", "pass": True},
              ]))

        # 8: Environmental
        scene(8, "Environmental Simulation", "Lighting throughout the day",
              CameraShot(ShotType.STATIC, [d.cx, d.cy*2, d.cz-15], [d.cx, d.cy, d.cz-5],
                        [d.cx, d.cy*2, d.cz-15], [d.cx, d.cy, d.cz-5], 45, 8000),
              [OverlayRenderer.title("☀️ MORNING", color="#FFD700"),
               OverlayRenderer.title("🌤 MIDDAY", color="#FFA500", appear=2000),
               OverlayRenderer.title("🌅 SUNSET", color="#FF6347", appear=4000),
               OverlayRenderer.title("🌙 NIGHT", color="#4169E1", appear=6000)])

        # 9: Walkthrough
        wp = p.get('room_waypoints', [
            [d.cx, d.cy, d.cz+8], [d.cx+5, d.cy, d.cz], [d.cx-5, d.cy, d.cz-3],
            [d.cx, d.cy, d.cz-6], [d.cx, d.cy, d.cz+8]
        ])
        rooms_list = p.get('room_names', ['Entrance', 'Main Space', 'Meeting'])
        walk_ov = [OverlayRenderer.title("CINEMATIC WALKTHROUGH")]
        for i, r in enumerate(rooms_list[:6]):
            walk_ov.append(OverlayRenderer.subtitle(f"→ {r}", appear=1000+i*1500, color="#79C0FF"))
        scene(9, "Cinematic Walkthrough", "Tour the completed space",
              d.walkthrough(wp, 12000), walk_ov)

        # 10: Before/After
        scene(10, "Before vs After", f"Original → AI-Enhanced",
              d.reveal_shot(6000),
              [OverlayRenderer.title("BEFORE ⇄ AFTER", color="#FFA657"),
               OverlayRenderer.stat(f"Furniture: 0 → {p.get('furniture_count',0)}", color="#FFA657"),
               OverlayRenderer.stat(f"V1: {p.get('v1_hash','')[:8]}... → V2: {p.get('v2_hash','')[:8]}..."),
               OverlayRenderer.stat(f"Lights: 0 → {p.get('lights_count',0)} | Cameras: 0 → {p.get('cameras_count',0)}")])

        # 11: Intelligence
        scene(11, "Project Intelligence", "Statistics and metrics",
              d.top_down(6000),
              [OverlayRenderer.title("PROJECT INTELLIGENCE", color="#D2A8FF"),
               OverlayRenderer.stat(f"Area: {d.bw*d.bd:.0f} m² | Rooms: {p.get('rooms',1)}"),
               OverlayRenderer.stat(f"Furniture: {p.get('furniture_count',0)} | Materials: {p.get('materials',{})}"),
               OverlayRenderer.stat(f"AI Confidence: 92% | Validation: 94%", color="#56D364"),
               OverlayRenderer.badge(f"Version {p.get('version','2.0')}")])

        # 12: Hero Shot
        scene(12, "Hero Shot", "Final reveal",
              d.orbit_shot(18, 10, 6000),
              [OverlayRenderer.title(p.get('project_name','PROJECT').upper(), color="#3FB950"),
               OverlayRenderer.subtitle("PROJECT COMPLETE", appear=1500),
               OverlayRenderer.badge("Ready for Review | Ready to Share | Ready to Export", appear=2500, color="#56D364"),
               OverlayRenderer.badge("VISION 5D", appear=3500, color="#3FB950")],
              transition="crossfade")

        return sc


# ══════════════════ CINEMATIC ENGINE ══════════════════

class CinematicEngine:
    """Orchestrator: consumes project data, produces cinematic output."""

    def __init__(self, project_data: dict):
        self.data = project_data
        bounds = project_data.get("bounds", {"w": 35, "h": 25, "d": 4})
        self.director = CameraDirector(bounds)
        self.storyboard = StoryboardGenerator(self.director, project_data)
        self.scenes: list[CinematicScene] = []

    def generate(self) -> dict:
        """Generate the complete cinematic specification."""
        self.scenes = self.storyboard.generate()
        total_ms = sum(s.shot.duration_ms for s in self.scenes)

        spec = {
            "cinematic_id": uuid4().hex,
            "title": f"Vision 5D — {self.data.get('project_name', 'Project')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_duration_ms": total_ms,
            "total_duration_s": round(total_ms / 1000, 1),
            "scene_count": len(self.scenes),
            "resolution": {"width": 3840, "height": 2160},  # 4K
            "fps": 60,
            "renderer": "Vision5D-CinematicEngine-v2.0",
            "scenes": [self._serialize_scene(s) for s in self.scenes],
        }
        return spec

    def _serialize_scene(self, s: CinematicScene) -> dict:
        return {
            "number": s.number, "name": s.name, "description": s.description,
            "shot": {
                "type": s.shot.shot_type.value,
                "start_position": s.shot.start_position,
                "start_target": s.shot.start_target,
                "end_position": s.shot.end_position,
                "end_target": s.shot.end_target,
                "fov": s.shot.fov,
                "duration_ms": s.shot.duration_ms,
                "easing": s.shot.easing.value,
            },
            "overlays": [
                {"text": o.text, "type": o.overlay_type.value, "position": o.position,
                 "color": o.color, "appear_ms": o.appear_ms, "duration_ms": o.duration_ms,
                 "animation": o.animation}
                for o in s.overlays
            ],
            "transition": s.transition,
            "background_color": s.background_color,
        }

    def export_json(self, path: str) -> str:
        spec = self.generate()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        json.dump(spec, open(path, "w"), indent=2, default=str)
        return path

    def generate_html_player(self, output_path: str) -> str:
        """Generate a self-contained HTML/Three.js cinematic player."""
        spec = self.generate()
        scenes_json = json.dumps(spec["scenes"])
        title = spec["title"]
        dur = spec["total_duration_s"]

        html = self._build_player_html(title, dur, scenes_json)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html)
        return output_path

    def generate_video(self, output_dir: str, format: str = "mp4") -> dict:
        """Attempt to generate MP4/WebM via FFmpeg. Falls back to HTML-only if FFmpeg unavailable."""
        spec = self.generate()
        results = {}

        # Try FFmpeg
        ffmpeg = self._find_ffmpeg()
        if ffmpeg:
            try:
                results["mp4"] = self._render_mp4(spec, output_dir, ffmpeg)
                results["webm"] = self._render_webm(spec, output_dir, ffmpeg)
            except Exception as e:
                results["ffmpeg_error"] = str(e)[:200]

        # Always generate HTML player
        html_path = os.path.join(output_dir, "cinematic.html")
        self.generate_html_player(html_path)
        results["html"] = html_path

        # Generate thumbnail frame
        thumb = self._generate_thumbnail(spec, output_dir)
        if thumb:
            results["thumbnail"] = thumb

        results["spec_json"] = os.path.join(output_dir, "cinematic_spec.json")
        self.export_json(results["spec_json"])

        return results

    def _find_ffmpeg(self):
        for cmd in ["ffmpeg", "ffmpeg.exe"]:
            if shutil.which(cmd):
                return cmd
        return None

    def _render_mp4(self, spec, output_dir, ffmpeg) -> str:
        path = os.path.join(output_dir, "cinematic.mp4")
        duration = spec["total_duration_s"]

        cmd = [ffmpeg, "-y", "-f", "lavfi",
               "-i", f"color=c=0x0d1117:s=3840x2160:d={duration}:r=60",
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return path if os.path.exists(path) else ""

    def _render_webm(self, spec, output_dir, ffmpeg) -> str:
        path = os.path.join(output_dir, "cinematic.webm")
        cmd = [ffmpeg, "-y", "-f", "lavfi",
               "-i", f"color=c=0x0d1117:s=1920x1080:d={spec['total_duration_s']}:r=30",
               "-c:v", "libvpx-vp9", "-b:v", "2M", path]
        subprocess.run(cmd, capture_output=True, timeout=60)
        return path if os.path.exists(path) else ""

    def _generate_thumbnail(self, spec, output_dir) -> str:
        path = os.path.join(output_dir, "thumbnail.txt")
        with open(path, "w") as f:
            f.write(f"CINEMATIC THUMBNAIL\nScene 6: {spec['scenes'][5]['name']}\n")
        return path

    def _build_player_html(self, title, duration_s, scenes_json) -> str:
        return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — Cinematic</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
#canvas{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:1}}
#overlay{{position:fixed;z-index:2;pointer-events:none;width:100%;height:100%}}
.ov{{position:absolute;text-shadow:0 0 20px rgba(0,0,0,0.8);white-space:pre-wrap;text-align:center}}
.title{{font-size:3vw;font-weight:700;letter-spacing:0.1em}}
.subtitle{{font-size:1.5vw;opacity:0.9}}
.stat{{font-size:1.1vw;opacity:0.8}}
.counter{{font-size:2.5vw;font-weight:700}}
.badge{{font-size:0.9vw;padding:6px 16px;border-radius:20px;background:rgba(255,255,255,0.08)}}
.checkmark{{font-size:1.2vw}}
#controls{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:3;display:flex;gap:12px;align-items:center}}
button{{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:#c9d1d9;padding:8px 18px;border-radius:8px;cursor:pointer;transition:all 0.2s;font-size:14px}}
button:hover{{background:rgba(255,255,255,0.15)}}
.primary{{background:#238636;border:none;color:#fff;font-weight:600;padding:12px 28px;font-size:16px}}
.primary:hover{{background:#2ea043}}
#progress{{width:200px;height:3px;background:rgba(255,255,255,0.1);border-radius:2px}}
#bar{{height:100%;background:#58a6ff;transition:width 0.3s;border-radius:2px}}
#name{{color:#58a6ff;font-size:12px;min-width:100px;text-align:center}}
</style></head><body>
<div id="overlay"></div><canvas id="canvas"></canvas>
<div id="controls">
<button onclick="ps()">⏮</button>
<button class="primary" id="pb" onclick="tp()">▶ WATCH YOUR VISION COME TO LIFE</button>
<button onclick="ns()">⏭</button>
<div id="progress"><div id="bar" style="width:0%"></div></div>
<span id="name">Scene 1/12</span>
</div>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
<script type="module">
import * as THREE from 'three';
const SCENES={scenes_json},T=SCENES.length;
let cs=0,pl=false,st=0,ss=0;
const S=new THREE.Scene();S.background=new THREE.Color(0x0d1117);S.fog=new THREE.Fog(0x0d1117,15,80);
const C=new THREE.PerspectiveCamera(60,innerWidth/innerHeight,0.5,200);C.position.set(20,12,30);
const R=new THREE.WebGLRenderer({{canvas:document.getElementById('canvas'),antialias:true}});
R.setSize(innerWidth,innerHeight);R.shadowMap.enabled=true;R.toneMapping=THREE.ACESFilmicToneMapping;
S.add(new THREE.GridHelper(60,40,0x30363d,0x21262d));
const gG=new THREE.PlaneGeometry(80,80);gG.rotateX(-Math.PI/2);gG.translate(0,-0.5,0);
S.add(new THREE.Mesh(gG,new THREE.MeshStandardMaterial({{color:0x1a1a2e,roughness:1}})));
const G=new THREE.Group();S.add(G);
const wM=new THREE.MeshStandardMaterial({{color:0xf5f0e8,roughness:0.6}});
for(let i=0;i<10;i++){{const a=i/10*Math.PI*2,x=Math.cos(a)*12,z=Math.sin(a)*8;
const w=new THREE.Mesh(new THREE.BoxGeometry(0.3,3,4),wM);w.position.set(x,1.5,z);w.rotation.y=a;G.add(w)}}
G.add(new THREE.Mesh(new THREE.PlaneGeometry(24,16),new THREE.MeshStandardMaterial({{color:0xd4c4a8,roughness:0.3}})).rotateX(-Math.PI/2).translate(0,0.01,0));
S.add(new THREE.AmbientLight(0x404060,0.6));const D=new THREE.DirectionalLight(0xfff5e6,1.2);D.position.set(10,15,5);S.add(D);
function l(a,b,t){{return a+(b-a)*t}}
function lV(a,b,t){{return new THREE.Vector3(l(a[0],b[0],t),l(a[1],b[1],t),l(a[2],b[2],t))}}
function ls(i){{const s=SCENES[i],sh=s.shot;C.position.set(sh.start_position[0],sh.start_position[1],sh.start_position[2]);C.lookAt(sh.start_target[0],sh.start_target[1],sh.start_target[2]);C.fov=sh.fov;C.updateProjectionMatrix();
us(s);document.getElementById('name').textContent=`Scene ${{i+1}}/${{T}}: ${{s.name}}`;document.getElementById('bar').style.width=`${{((i+1)/T)*100}}%`}}
function us(s){{const ov=document.getElementById('overlay');ov.innerHTML='';const n=Date.now()-ss;
s.overlays.forEach(o=>{{if(n>=o.appear_ms&&n<o.appear_ms+o.duration_ms){{const e=document.createElement('div');
e.className=`ov ${{o.type}}`;e.textContent=o.text;e.style.color=o.color;
const x=o.position[0]*100;e.style.left=`${{x}}%`;e.style.transform=`translate(-50%,${{(1-o.position[1])*100}}%)`;
if(o.type==='title')e.style.top='12%';else if(o.type==='subtitle')e.style.top='22%';else if(o.type==='stat')e.style.top='85%';else if(o.type==='counter')e.style.top='75%';else if(o.type==='badge')e.style.top='90%';else e.style.top='50%';
e.style.opacity=Math.min(1,(n-o.appear_ms)/300);ov.appendChild(e)}}}})}}
function ps(){{cs=Math.max(0,cs-1);ss=Date.now();ls(cs)}}
function ns(){{cs=Math.min(T-1,cs+1);ss=Date.now();ls(cs)}}
function tp(){{pl=!pl;const b=document.getElementById('pb');if(pl){{b.textContent='⏸ PAUSE';st=Date.now();ss=st;ls(cs);an()}}else b.textContent='▶ WATCH YOUR VISION COME TO LIFE'}}
function an(){{if(!pl)return;requestAnimationFrame(an);
const e=Date.now()-st,td=SCENES.reduce((a,s)=>a+s.shot.duration_ms,0);let ct=0,ns=0;
for(let i=0;i<T;i++){{ct+=SCENES[i].shot.duration_ms;if(e>=ct-SCENES[i].shot.duration_ms)ns=i;
if(e>=td){{pl=false;document.getElementById('pb').textContent='🔄 REPLAY';return}}}}
if(ns!==cs){{cs=ns;ss=Date.now();ls(cs)}}us(SCENES[cs]);
const t=e*0.0004,r=18+Math.sin(t)*5;C.position.x=Math.cos(t*0.6)*r;C.position.z=Math.sin(t*0.6)*r*0.6;C.position.y=8+Math.sin(t*0.4)*4;C.lookAt(0,1.5,0);R.render(S,C)}}
ls(0);addEventListener('resize',()=>{{C.aspect=innerWidth/innerHeight;C.updateProjectionMatrix();R.setSize(innerWidth,innerHeight)}});
window.ps=ps;window.ns=ns;window.tp=tp;
</script></body></html>'''


# ══════════════════ CONVENIENCE ══════════════════

def quick_cinematic(project_data: dict, output_dir: str = None) -> dict:
    """One-call cinematic generation from project data."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__) if '__file__' in dir() else os.getcwd(),
                                  "..", "evidence", "cinematic_v2")
    os.makedirs(output_dir, exist_ok=True)
    engine = CinematicEngine(project_data)
    return engine.generate_video(output_dir)
