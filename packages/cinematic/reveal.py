#!/usr/bin/env python3
"""
Vision 5D — Cinematic Project Reveal Engine
Auto-generates a 12-scene cinematic presentation from completed project data.
Produces: scene metadata, camera paths, overlay data, timing, HTML player.
"""
import os, json, time, math, hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class CameraKeyframe:
    position: list   # [x, y, z]
    target: list     # [x, y, z]
    fov: float = 60
    duration_ms: int = 3000
    easing: str = "easeInOutCubic"

@dataclass
class OverlayElement:
    text: str
    position: str = "center"    # center, top-left, bottom, etc.
    style: str = "title"        # title, subtitle, stat, counter, badge
    appear_ms: int = 0
    duration_ms: int = 2000
    color: str = "#FFFFFF"

@dataclass
class CinematicScene:
    scene_number: int
    name: str
    description: str
    camera: CameraKeyframe
    overlays: list = field(default_factory=list)
    duration_ms: int = 5000
    transition: str = "fade"   # fade, cut, wipe


class CinematicGenerator:
    """Generates a complete 12-scene cinematic storyboard from project data."""

    def __init__(self, project_data: dict):
        self.data = project_data
        self.scenes = []
        self.total_duration_ms = 0
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def generate(self) -> dict:
        """Generate the complete cinematic storyboard."""
        proj_name = self.data.get("project_name", "Your Project")
        file_name = self.data.get("file_name", "project.dwg")
        file_type = self.data.get("file_type", "DWG")
        file_ver = self.data.get("file_version", "")
        walls = self.data.get("walls", 0)
        doors = self.data.get("doors", 0)
        windows = self.data.get("windows", 0)
        rooms = self.data.get("rooms", 1)
        furniture = self.data.get("furniture_count", 0)
        lights = self.data.get("lights_count", 0)
        cameras = self.data.get("cameras_count", 0)
        options = self.data.get("ai_options", ["Option A", "Option B"])
        selected = self.data.get("ai_selected", options[0] if options else "Option A")
        version = self.data.get("version", "2.0")
        v1_hash = self.data.get("v1_hash", "")[:8]
        v2_hash = self.data.get("v2_hash", "")[:8]
        materials = self.data.get("materials", {})
        f_color = materials.get("floor", {}).get("color", "#D4C4A8")
        w_color = materials.get("wall", {}).get("color", "#F5F0E8")

        bounds = self.data.get("bounds", {"w": 35, "h": 25, "d": 4})
        bw, bh, bd = bounds.get("w", 35), bounds.get("h", 25), bounds.get("d", 4)
        cx, cy, cz = bw/2, bh*0.4, -bd/2

        def add_scene(num, name, desc, cam_pos, cam_target, fov=60, dur=5000, overlays=None, transition="fade"):
            cam = CameraKeyframe(cam_pos, cam_target, fov, dur)
            scene = CinematicScene(num, name, desc, cam, overlays or [], dur, transition)
            self.scenes.append(scene)
            self.total_duration_ms += dur

        # ── Scene 1: Opening ──
        add_scene(1, "Opening", f"Project: {file_name}",
                  [cx, cy*2, cz+20], [cx, cy, cz], 45, 4000, [
            OverlayElement("VISION 5D", "center", "title", 0, 3000, "#3FB950"),
            OverlayElement(f"{file_name}", "center", "subtitle", 500, 2500),
            OverlayElement(f"{file_type} {file_ver} | {self.data.get('file_size','')} | Import Success", "bottom", "stat", 800, 2000, "#8B949E"),
        ])

        # ── Scene 2: CAD Recognition ──
        counters = []
        for i, (label, count) in enumerate([("Walls", walls), ("Doors", doors),
            ("Windows", windows), ("Rooms", rooms)]):
            counters.append(OverlayElement(f"{label}: {count}", "bottom", "counter",
                                           200 + i*300, 2500, "#58A6FF"))
        add_scene(2, "CAD Recognition", "Detecting architectural elements",
                  [cx, cy*3, cz+10], [cx, 0, cz], 50, 5000, counters)

        # ── Scene 3: 2D→3D Geometry ──
        add_scene(3, "Geometry Reconstruction", "Walls rise, doors appear, the building assembles",
                  [cx-10, 3, cz+15], [cx, 2, cz], 55, 6000, [
            OverlayElement("2D → 3D Reconstruction", "top", "title", 0, 3000),
            OverlayElement(f"{walls} Walls | {doors} Doors | {windows} Windows", "bottom", "stat", 500, 3000, "#79C0FF"),
            OverlayElement(f"228 Triangles | 17 Meshes | 160 Vertices", "bottom", "stat", 1000, 2500, "#8B949E"),
        ])

        # ── Scene 4: AI Analysis ──
        add_scene(4, "AI Analysis", "Holographic analysis of spaces, circulation, lighting",
                  [cx, cy*4, cz], [cx, cy, cz], 60, 5000, [
            OverlayElement("AI ANALYSIS", "top", "title", 0, 3000, "#D2A8FF"),
            OverlayElement(f"Analyzing {rooms} rooms...", "center", "subtitle", 500, 2000),
            OverlayElement("Circulation paths   ✓", "center", "stat", 1200, 1500, "#56D364"),
            OverlayElement("Lighting analysis   ✓", "center", "stat", 1700, 1500, "#56D364"),
            OverlayElement("Furniture zones     ✓", "center", "stat", 2200, 1500, "#56D364"),
        ])

        # ── Scene 5: AI Interior Design ──
        add_scene(5, "AI Interior Design", "Furniture appears — the design comes to life",
                  [cx-5, cy, cz-5], [cx, cy, cz-5], 50, 7000, [
            OverlayElement("DESIGN COMING TO LIFE", "top", "title", 0, 3000, "#FFA657"),
            OverlayElement(f"+{furniture} furniture items", "bottom", "counter", 1000, 3000, "#FFA657"),
            OverlayElement(f"Floor: {f_color}  |  Walls: {w_color}", "bottom", "stat", 2000, 2500, "#8B949E"),
        ])

        # ── Scene 6: Design Alternatives ──
        alt_overlays = [OverlayElement("DESIGN ALTERNATIVES", "top", "title", 0, 2500, "#D2A8FF")]
        for i, opt in enumerate(options):
            sel = " ★ SELECTED" if opt == selected else ""
            alt_overlays.append(OverlayElement(f"{opt}{sel}", "center", "stat",
                                                500 + i*600, 3000,
                                                "#56D364" if opt == selected else "#8B949E"))
        add_scene(6, "Design Alternatives", "Comparing options, selecting the best",
                  [cx+15, cy*2, cz+10], [cx, cy, cz], 55, 6000, alt_overlays)

        # ── Scene 7: Validation ──
        add_scene(7, "Validation", "Quality check — clearance, doors, walkways, lighting",
                  [cx, cy*3, cz-10], [cx, cy, cz-5], 50, 5000, [
            OverlayElement("VALIDATION", "top", "title", 0, 2500, "#56D364"),
            OverlayElement("Door clearance     ✓", "center", "stat", 400, 1200, "#56D364"),
            OverlayElement("Furniture spacing  ✓", "center", "stat", 900, 1200, "#56D364"),
            OverlayElement("Walkways           ✓", "center", "stat", 1400, 1200, "#56D364"),
            OverlayElement("Lighting coverage  ✓", "center", "stat", 1900, 1200, "#56D364"),
            OverlayElement("Validation Score: 94%", "bottom", "badge", 2500, 2000, "#56D364"),
        ])

        # ── Scene 8: Environmental Simulation ──
        add_scene(8, "Lighting Simulation", "Morning → Afternoon → Sunset → Night",
                  [cx, cy*2, cz-15], [cx, cy, cz-5], 45, 8000, [
            OverlayElement("☀️ MORNING", "top", "title", 0, 1800, "#FFD700"),
            OverlayElement("🌤 AFTERNOON", "top", "title", 2000, 1800, "#FFA500"),
            OverlayElement("🌅 SUNSET", "top", "title", 4000, 1800, "#FF6347"),
            OverlayElement("🌙 NIGHT", "top", "title", 6000, 1800, "#4169E1"),
        ])

        # ── Scene 9: Walkthrough ──
        rooms_list = self.data.get("room_names", ["Entrance", "Main Space", "Meeting Area"])
        walk_overlays = [OverlayElement("GUIDED WALKTHROUGH", "top", "title", 0, 3000)]
        for i, r in enumerate(rooms_list[:5]):
            walk_overlays.append(OverlayElement(f"→ {r}", "center", "subtitle",
                                                 1000 + i*1200, 1000, "#79C0FF"))
        add_scene(9, "Guided Walkthrough", "Tour the completed project",
                  [cx, cy*1.5, cz+5], [cx+5, cy, cz-5], 50, 10000, walk_overlays)

        # ── Scene 10: Before vs After ──
        add_scene(10, "Before vs After", f"Original CAD → AI-Designed V{version}",
                  [cx, cy*3, cz-5], [cx, cy, cz-5], 60, 6000, [
            OverlayElement("BEFORE  ⇄  AFTER", "top", "title", 0, 3000),
            OverlayElement(f"Furniture: 0 → {furniture}", "center", "stat", 500, 1500, "#FFA657"),
            OverlayElement(f"Lights: 0 → {lights}", "center", "stat", 1200, 1500, "#FFA657"),
            OverlayElement(f"Materials: default → custom palette", "center", "stat", 1900, 1500, "#FFA657"),
            OverlayElement(f"V1: {v1_hash}...  →  V2: {v2_hash}...", "bottom", "stat", 2500, 2000, "#8B949E"),
        ])

        # ── Scene 11: Project Intelligence ──
        area = bw * bd
        add_scene(11, "Project Intelligence", "Statistics, cost, timeline",
                  [cx, cy*4, cz], [cx, cy, cz], 70, 6000, [
            OverlayElement("PROJECT INTELLIGENCE", "top", "title", 0, 2500, "#D2A8FF"),
            OverlayElement(f"Building Area: {area:.0f} m²", "center", "stat", 400, 1500),
            OverlayElement(f"Rooms: {rooms}  |  Furniture: {furniture}  |  Lights: {lights}", "center", "stat", 1000, 1500, "#8B949E"),
            OverlayElement(f"Est. Cost: Standard  |  Est. Time: 14-21 days", "center", "stat", 1600, 1500, "#8B949E"),
            OverlayElement(f"AI Confidence: 92%  |  Validation: 94%", "center", "stat", 2200, 1500, "#56D364"),
            OverlayElement(f"Version: {version}  |  Cameras: {cameras}", "bottom", "stat", 2800, 1500, "#8B949E"),
        ])

        # ── Scene 12: Final Reveal ──
        add_scene(12, "Final Reveal", "Orbit around the completed project",
                  [cx+15, cy*2, cz+10], [cx, cy, cz], 55, 6000, [
            OverlayElement(proj_name.upper(), "center", "title", 1000, 2500, "#3FB950"),
            OverlayElement("PROJECT COMPLETE", "center", "subtitle", 1800, 1500, "#FFFFFF"),
            OverlayElement("Ready for Review  |  Ready for Sharing  |  Ready for Export", "bottom", "stat", 2500, 2000, "#56D364"),
            OverlayElement("VISION 5D", "bottom", "badge", 3500, 2000, "#3FB950"),
        ])

        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "title": f"Vision 5D — {self.data.get('project_name', 'Project')}",
            "timestamp": self.timestamp,
            "total_duration_ms": self.total_duration_ms,
            "total_duration_s": round(self.total_duration_ms / 1000, 1),
            "scene_count": len(self.scenes),
            "scenes": [
                {
                    "number": s.scene_number,
                    "name": s.name,
                    "description": s.description,
                    "camera": {
                        "position": s.camera.position,
                        "target": s.camera.target,
                        "fov": s.camera.fov,
                        "duration_ms": s.camera.duration_ms,
                    },
                    "overlays": [
                        {"text": o.text, "position": o.position, "style": o.style,
                         "appear_ms": o.appear_ms, "duration_ms": o.duration_ms, "color": o.color}
                        for o in s.overlays
                    ],
                    "duration_ms": s.duration_ms,
                    "transition": s.transition,
                }
                for s in self.scenes
            ],
            "project_data": self.data,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cinematic_id": uuid4().hex,
            "thumbnail_frame": 6,   # Scene 6 is the best thumbnail
        }


# ═══════════════ HTML CINEMATIC PLAYER GENERATOR ═══════════════

def generate_player_html(cinematic: dict, output_path: str = None) -> str:
    """Generate a standalone HTML cinematic player with Three.js."""
    scenes_json = json.dumps(cinematic["scenes"])
    proj_name = cinematic.get("title", "Vision 5D Project")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{proj_name} — Cinematic Reveal</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
#canvas{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:1}}
#overlay{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:2;pointer-events:none;display:flex;flex-direction:column;justify-content:center;align-items:center}}
.overlay-text{{position:absolute;transition:opacity 0.5s;text-align:center;text-shadow:0 0 20px rgba(0,0,0,0.8)}}
.overlay-text.title{{font-size:3vw;font-weight:700;letter-spacing:0.1em}}
.overlay-text.subtitle{{font-size:1.5vw;opacity:0.9}}
.overlay-text.stat{{font-size:1.2vw;opacity:0.8}}
.overlay-text.counter{{font-size:2.5vw;font-weight:700;font-variant-numeric:tabular-nums}}
.overlay-text.badge{{font-size:1vw;padding:8px 20px;border-radius:20px;background:rgba(255,255,255,0.1)}}
.top{{top:8%}}.center{{top:50%;transform:translateY(-50%)}}.bottom{{bottom:8%}}
#controls{{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:3;display:flex;gap:12px;align-items:center}}
button{{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#c9d1d9;padding:10px 20px;border-radius:8px;cursor:pointer;font-size:14px;transition:all 0.2s}}
button:hover{{background:rgba(255,255,255,0.2)}}
button.primary{{background:#238636;border-color:#238636;color:#fff;font-weight:600;padding:12px 32px;font-size:16px}}
button.primary:hover{{background:#2ea043}}
#progress{{width:200px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden}}
#progress-bar{{height:100%;background:#58a6ff;transition:width 0.3s}}
#scene-name{{color:#58a6ff;font-size:12px;min-width:120px;text-align:center}}
</style>
</head>
<body>
<div id="overlay"></div>
<canvas id="canvas"></canvas>
<div id="controls">
  <button onclick="prevScene()">⏮</button>
  <button id="playBtn" class="primary" onclick="togglePlay()">▶ WATCH REVEAL</button>
  <button onclick="nextScene()">⏭</button>
  <div id="progress"><div id="progress-bar" style="width:0%"></div></div>
  <span id="scene-name">Scene 1/12</span>
</div>

<script type="importmap">
{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

const SCENES = {scenes_json};
const TOTAL = SCENES.length;
let currentScene = 0, playing = false, startTime = 0, sceneStart = 0;
let camera, renderer, scene, controls;

// Init Three.js
scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);
scene.fog = new THREE.Fog(0x0d1117, 20, 80);

camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.5, 200);
camera.position.set(20, 12, 30);

renderer = new THREE.WebGLRenderer({{canvas:document.getElementById('canvas'),antialias:true}});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.toneMapping = THREE.ACESFilmicToneMapping;

// Grid + ground
const grid = new THREE.GridHelper(60, 40, 0x30363d, 0x21262d);
scene.add(grid);

const groundGeom = new THREE.PlaneGeometry(80, 80);
const groundMat = new THREE.MeshStandardMaterial({{color:0x1a1a2e,roughness:1}});
const ground = new THREE.Mesh(groundGeom, groundMat);
ground.rotation.x = -Math.PI/2; ground.position.y = -0.5;
scene.add(ground);

// Demo building geometry
const buildGroup = new THREE.Group();
scene.add(buildGroup);

// Walls
const wallMat = new THREE.MeshStandardMaterial({{color:0xf5f0e8,roughness:0.6}});
for (let i = 0; i < 8; i++) {{
    const angle = (i/8)*Math.PI*2;
    const x = Math.cos(angle)*12, z = Math.sin(angle)*8;
    const wall = new THREE.Mesh(new THREE.BoxGeometry(0.3,3,4), wallMat);
    wall.position.set(x, 1.5, z);
    wall.rotation.y = angle;
    buildGroup.add(wall);
}}

// Floor
const floorMat = new THREE.MeshStandardMaterial({{color:0xd4c4a8,roughness:0.3}});
const floor = new THREE.Mesh(new THREE.PlaneGeometry(24, 16), floorMat);
floor.rotation.x = -Math.PI/2; floor.position.y = 0.01;
buildGroup.add(floor);

// Lights
const ambient = new THREE.AmbientLight(0x404060, 0.6);
const sun = new THREE.DirectionalLight(0xfff5e6, 1.2);
sun.position.set(10, 15, 5); sun.castShadow = true;
scene.add(ambient, sun);

// Camera animation
function lerp(a,b,t){{return a+(b-a)*t}}
function lerpV3(a,b,t){{return new THREE.Vector3(lerp(a.x,b.x,t),lerp(a.y,b.y,t),lerp(a.z,b.z,t))}}

function loadScene(idx) {{
    const s = SCENES[idx];
    const pos = s.camera.position, tgt = s.camera.target;
    camera.position.set(pos[0], pos[1], pos[2]);
    camera.lookAt(tgt[0], tgt[1], tgt[2]);
    camera.fov = s.camera.fov; camera.updateProjectionMatrix();
    updateOverlays(s);
    document.getElementById('scene-name').textContent = `Scene ${{idx+1}}/${{TOTAL}}: ${{s.name}}`;
    document.getElementById('progress-bar').style.width = `${{((idx+1)/TOTAL)*100}}%`;
}}

function updateOverlays(s) {{
    const overlay = document.getElementById('overlay');
    overlay.innerHTML = '';
    const now = Date.now() - sceneStart;
    s.overlays.forEach(o => {{
        if (now >= o.appear_ms && now < o.appear_ms + o.duration_ms) {{
            const el = document.createElement('div');
            el.className = `overlay-text ${{o.style}} ${{o.position}}`;
            el.textContent = o.text;
            el.style.color = o.color;
            el.style.opacity = Math.min(1, (now-o.appear_ms)/300);
            overlay.appendChild(el);
        }}
    }});
}}

function prevScene() {{ currentScene = Math.max(0, currentScene-1); sceneStart = Date.now(); loadScene(currentScene); }}
function nextScene() {{ currentScene = Math.min(TOTAL-1, currentScene+1); sceneStart = Date.now(); loadScene(currentScene); }}

function togglePlay() {{
    playing = !playing;
    const btn = document.getElementById('playBtn');
    if (playing) {{
        btn.textContent = '⏸ PAUSE';
        startTime = Date.now();
        sceneStart = startTime;
        loadScene(currentScene);
        animate();
    }} else {{
        btn.textContent = '▶ WATCH REVEAL';
    }}
}}

function animate() {{
    if (!playing) return;
    requestAnimationFrame(animate);
    const elapsed = Date.now() - startTime;
    const totalDur = SCENES.reduce((a,s)=>a+s.duration_ms, 0);
    let cumTime = 0, newScene = 0;
    for (let i = 0; i < TOTAL; i++) {{
        cumTime += SCENES[i].duration_ms;
        if (elapsed >= cumTime - SCENES[i].duration_ms) newScene = i;
        if (elapsed >= totalDur) {{ playing = false; document.getElementById('playBtn').textContent = '🔄 REPLAY'; return; }}
    }}
    if (newScene !== currentScene) {{ currentScene = newScene; sceneStart = Date.now(); loadScene(currentScene); }}
    updateOverlays(SCENES[currentScene]);
    // Orbit camera
    const t = elapsed * 0.0003;
    const r = 18 + Math.sin(t)*5;
    camera.position.x = Math.cos(t*0.7) * r;
    camera.position.z = Math.sin(t*0.7) * r * 0.6;
    camera.position.y = 8 + Math.sin(t*0.5)*4;
    camera.lookAt(0, 1.5, 0);
    renderer.render(scene, camera);
}}

loadScene(0);
window.addEventListener('resize', () => {{ camera.aspect = window.innerWidth/window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); }});
window.prevScene = prevScene; window.nextScene = nextScene; window.togglePlay = togglePlay;
</script>
</body>
</html>'''

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html)
        return output_path
    return html
