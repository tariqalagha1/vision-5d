#!/usr/bin/env python3
"""
Vision 5D — Real Cinematic Video Exporter (V5D-2.0-CINEMATIC-VIDEO-EXPORT-001)
Renders the 14-scene luxury cinematic into real MP4/WebM video files.
Frame-by-frame rendering with Pillow, encoding with FFmpeg.
"""
import os, sys, json, time, math, hashlib, subprocess, tempfile, shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont

# ═══════════════ CONFIG ═══════════════
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "projects", "cinematic_v2")
VIDEO_DIR = os.path.join(OUTPUT_DIR, "video")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "evidence", "V5D-2.0-CINEMATIC-VIDEO-EXPORT-001")

for d in [VIDEO_DIR, IMAGE_DIR, REPORT_DIR, LOG_DIR, EVIDENCE_DIR]:
    os.makedirs(d, exist_ok=True)

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "evidence", "cinematic_luxury", "luxury_cinematic.json")
FRAMES_DIR = tempfile.mkdtemp(prefix="v5d_frames_")
SOURCE_HTML = os.path.join(os.path.dirname(__file__), "..", "apps", "web", "cinematic_luxury.html")

RESOLUTION = (1920, 1080)  # Practical: 1080p. 4K target: (3840, 2160)
FPS = 30                    # Practical: 30fps. 60fps target: 60

ARTIFACTS = []
def record_artifact(name, atype, ext, path, mime, size=None):
    if size is None and os.path.exists(path):
        size = os.path.getsize(path)
    sha = ""
    if os.path.exists(path):
        with open(path, "rb") as f: sha = hashlib.sha256(f.read()).hexdigest()
    ARTIFACTS.append({
        "name": name, "type": atype, "extension": ext, "path": os.path.abspath(path),
        "mime_type": mime, "size_bytes": size or 0, "size_kb": round((size or 0)/1024, 1),
        "size_mb": round((size or 0)/1024/1024, 2), "sha256": sha,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "exists": os.path.exists(path),
    })
    return path

def log(msg):
    with open(os.path.join(LOG_DIR, "rendering.log"), "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")
    print(msg)


# ═══════════════ LOAD CINEMATIC SPEC ═══════════════
log("=== V5D-2.0-CINEMATIC-VIDEO-EXPORT-001 ===")
log(f"Loading: {SPEC_PATH}")
spec = json.load(open(SPEC_PATH))
scenes = spec["scenes"]
total_s = spec["total_duration_s"]
total_frames = int(total_s * FPS)
log(f"Scenes: {len(scenes)}  Duration: {total_s}s  Frames: {total_frames} @ {FPS}fps")

# Source integrity
spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
html_hash = hashlib.sha256(open(SOURCE_HTML, "rb").read()).hexdigest() if os.path.exists(SOURCE_HTML) else "N/A"
log(f"Spec SHA-256: {spec_hash[:16]}...")
log(f"HTML SHA-256: {html_hash[:16]}...")

# ═══════════════ FRAME RENDERER ═══════════════

def lerp(a, b, t): return a + (b - a) * t
def lerp3(a, b, t): return [lerp(a[0],b[0],t), lerp(a[1],b[1],t), lerp(a[2],b[2],t)]

# Camera projection (perspective)
def world_to_screen(pos, cam_pos, cam_target, fov_deg, w, h):
    """Simple perspective projection of a 3D point to 2D screen."""
    # Camera basis
    forward = [cam_target[0]-cam_pos[0], cam_target[1]-cam_pos[1], cam_target[2]-cam_pos[2]]
    fl = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    if fl < 0.001: fl = 1
    forward = [f/fl for f in forward]
    
    # Right vector
    world_up = [0, 1, 0]
    right = [forward[1]*world_up[2] - forward[2]*world_up[1],
             forward[2]*world_up[0] - forward[0]*world_up[2],
             forward[0]*world_up[1] - forward[1]*world_up[0]]
    rl = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    if rl < 0.001: right = [1, 0, 0]
    else: right = [r/rl for r in right]
    up = [right[1]*forward[2] - right[2]*forward[1],
          right[2]*forward[0] - right[0]*forward[2],
          right[0]*forward[1] - right[1]*forward[0]]
    
    # Relative position
    rx = pos[0] - cam_pos[0]; ry = pos[1] - cam_pos[1]; rz = pos[2] - cam_pos[2]
    
    # Dot products
    dx = rx*right[0] + ry*right[1] + rz*right[2]
    dy = rx*up[0] + ry*up[1] + rz*up[2]
    dz = rx*forward[0] + ry*forward[1] + rz*forward[2]
    
    if dz <= 0.1: return None  # Behind camera
    
    fov_rad = math.radians(fov_deg)
    scale = (h / 2) / (math.tan(fov_rad / 2) * dz)
    sx = w/2 + dx * scale
    sy = h/2 - dy * scale
    return (int(sx), int(sy))


def render_frame(scene_idx: int, t: float, width: int, height: int) -> Image.Image:
    """Render a single frame at scene index + time offset."""
    img = Image.new("RGB", (width, height), (13, 17, 23))  # #0d1117
    draw = ImageDraw.Draw(img)
    
    s = scenes[scene_idx]
    ca = s["camera"]
    scene_t = max(0, min(1, t))
    
    # Interpolate camera
    cam_pos = lerp3(ca["start_pos"], ca["end_pos"], scene_t)
    cam_tgt = lerp3(ca["start_target"], ca["end_target"], scene_t)
    fov = ca["fov"]
    
    # Draw ground plane (horizon line)
    horizon_y = int(height * 0.55)
    draw.rectangle([0, horizon_y, width, height], fill=(26, 26, 46))  # Ground
    
    # Draw grid lines
    for i in range(-20, 21):
        p1 = world_to_screen([i, 0, -15], cam_pos, cam_tgt, fov, width, height)
        p2 = world_to_screen([i, 0, 15], cam_pos, cam_tgt, fov, width, height)
        if p1 and p2:
            draw.line([p1, p2], fill=(33, 38, 45), width=1)
    
    for j in range(-15, 16, 2):
        p1 = world_to_screen([-20, 0, j], cam_pos, cam_tgt, fov, width, height)
        p2 = world_to_screen([20, 0, j], cam_pos, cam_tgt, fov, width, height)
        if p1 and p2:
            draw.line([p1, p2], fill=(33, 38, 45), width=1)
    
    # Draw walls (vertical lines)
    wall_color = (245, 240, 232)  # #f5f0e8
    for i in range(-8, 9, 2):
        b = world_to_screen([i, 0, -3], cam_pos, cam_tgt, fov, width, height)
        tp = world_to_screen([i, 3, -3], cam_pos, cam_tgt, fov, width, height)
        if b and tp:
            draw.line([b, tp], fill=wall_color, width=2)
        b2 = world_to_screen([i, 0, 3], cam_pos, cam_tgt, fov, width, height)
        tp2 = world_to_screen([i, 3, 3], cam_pos, cam_tgt, fov, width, height)
        if b2 and tp2:
            draw.line([b2, tp2], fill=wall_color, width=2)
    
    # Draw furniture — proper scale, category shapes, labels
    def rgb_to_tuple(hex_color):
        return (int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16))

    CATEGORY_COLORS = {
        "living": (196, 181, 165), "bedroom": (180, 170, 160), "dining": (170, 160, 150),
        "kitchen": (220, 215, 205), "bathroom": (240, 240, 240), "entry": (200, 190, 175),
        "storage": (180, 170, 155), "outdoor": (140, 130, 120), "plant": (76, 175, 80),
        "lighting": (255, 215, 0), "decor": (160, 150, 140), "laundry": (240, 240, 245),
    }
    for fi, furn in enumerate(s.get("furniture", [])):
        pos = furn["position"]
        dims = furn.get("dimensions", [1.0, 1.0, 1.0])
        cat = furn.get("category", "living")
        label = furn.get("label", "")[:20]
        color_hex = furn.get("color", "#C4B5A5")
        r, g, b = int(color_hex[1:3],16), int(color_hex[3:5],16), int(color_hex[5:7],16)
        cat_color = CATEGORY_COLORS.get(cat, (196, 181, 165))
        
        # Draw as 3D box — project corners
        w, h_f, d = dims[0], dims[1], dims[2]
        corners = [
            [pos[0]-w/2, 0, pos[2]-d/2], [pos[0]+w/2, 0, pos[2]-d/2],
            [pos[0]+w/2, 0, pos[2]+d/2], [pos[0]-w/2, 0, pos[2]+d/2],
            [pos[0]-w/2, h_f, pos[2]-d/2], [pos[0]+w/2, h_f, pos[2]-d/2],
            [pos[0]+w/2, h_f, pos[2]+d/2], [pos[0]-w/2, h_f, pos[2]+d/2],
        ]
        screen_pts = []
        for c in corners:
            sp = world_to_screen(c, cam_pos, cam_tgt, fov, width, height)
            if sp: screen_pts.append(sp)
        
        if len(screen_pts) >= 4:
            # Draw filled face
            xs = [p[0] for p in screen_pts]; ys = [p[1] for p in screen_pts]
            minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
            siz = max(8, int(math.sqrt((maxx-minx)*(maxy-miny)) / 3))
            draw.rectangle([minx, miny, maxx, maxy], fill=cat_color, outline=rgb_to_tuple(color_hex))
            # Label
            if siz > 12 and label:
                try:
                    font = ImageFont.truetype("arial.ttf", max(8, siz//3))
                except:
                    font = ImageFont.load_default()
                draw.text((minx+2, miny+2), label[:6], fill=(0,0,0), font=font)
    
    # Draw overlays
    elapsed_ms = t * s["duration_s"] * 1000
    for ov in s.get("overlays", []):
        appear_ms = ov.get("appear_s", 0) * 1000
        dur_ms = ov.get("duration_s", 2) * 1000
        if appear_ms <= elapsed_ms < appear_ms + dur_ms:
            alpha = min(1.0, (elapsed_ms - appear_ms) / 400)
            style = ov.get("style", "stat")
            color = ov.get("color", "#FFFFFF")
            text = ov.get("text", "")
            
            # Parse color
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            fill = (int(r*alpha), int(g*alpha), int(b*alpha))
            
            # Position + size by style
            if style == "title":
                y_pos = int(height * 0.10)
                font_size = int(width * 0.035)
            elif style == "subtitle":
                y_pos = int(height * 0.20)
                font_size = int(width * 0.016)
            elif style == "badge":
                y_pos = int(height * 0.90)
                font_size = int(width * 0.009)
            else:  # stat
                y_pos = int(height * 0.88)
                font_size = int(width * 0.011)
            
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            x_pos = (width - tw) // 2
            
            # Shadow
            draw.text((x_pos+2, y_pos+2), text, fill=(0, 0, 0), font=font)
            draw.text((x_pos, y_pos), text, fill=fill, font=font)
    
    return img


# ═══════════════ RENDER ALL FRAMES ═══════════════
log(f"\nRendering {total_frames} frames to {FRAMES_DIR}...")
t_start = time.time()

scene_start_frame = 0
frame_idx = 0
frames_rendered = 0
scene_frame_ranges = []

for si, s in enumerate(scenes):
    scene_frames = int(s["duration_s"] * FPS)
    scene_frame_ranges.append({
        "scene": si + 1, "name": s["name"], "start_frame": frame_idx,
        "end_frame": frame_idx + scene_frames - 1,
        "duration_s": s["duration_s"], "frame_count": scene_frames,
    })
    
    for fi in range(scene_frames):
        t = fi / max(scene_frames - 1, 1)  # 0..1 within scene
        frame = render_frame(si, t, RESOLUTION[0], RESOLUTION[1])
        frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_idx:06d}.png")
        frame.save(frame_path, "PNG")
        frame_idx += 1
        frames_rendered += 1
        
        if frame_idx % 300 == 0:
            elapsed = time.time() - t_start
            fps_actual = frame_idx / max(elapsed, 0.001)
            log(f"  Frame {frame_idx}/{total_frames} ({frame_idx*100/total_frames:.0f}%) — {fps_actual:.1f} fps actual")

render_time = time.time() - t_start
log(f"Rendered {frames_rendered} frames in {render_time:.0f}s ({frames_rendered/render_time:.1f} fps)")

# Save scene timeline
json.dump({"scene_frame_ranges": scene_frame_ranges, "total_frames": total_frames},
          open(os.path.join(REPORT_DIR, "scene_timeline.json"), "w"), indent=2)

# ═══════════════ ENCODE MP4 ═══════════════
log(f"\nEncoding MP4...")
mp4_path = os.path.join(VIDEO_DIR, "luxury_cinematic.mp4")
mp4_cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAMES_DIR, "frame_%06d.png"),
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}",
    mp4_path
]
mp4_result = subprocess.run(mp4_cmd, capture_output=True, text=True, timeout=300)
mp4_ok = os.path.exists(mp4_path)
log(f"MP4: {'OK' if mp4_ok else 'FAILED'} ({os.path.getsize(mp4_path) if mp4_ok else 0} bytes)")

# Encode WebM
log(f"Encoding WebM...")
webm_path = os.path.join(VIDEO_DIR, "luxury_cinematic.webm")
webm_cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAMES_DIR, "frame_%06d.png"),
    "-c:v", "libvpx-vp9", "-b:v", "2M", "-crf", "30",
    "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}",
    webm_path
]
webm_result = subprocess.run(webm_cmd, capture_output=True, text=True, timeout=300)
webm_ok = os.path.exists(webm_path)
log(f"WebM: {'OK' if webm_ok else 'FAILED'} ({os.path.getsize(webm_path) if webm_ok else 0} bytes)")

# ═══════════════ FFprobe validation ═══════════════
log(f"\nValidating output...")
for label, path in [("MP4", mp4_path), ("WebM", webm_path)]:
    if not os.path.exists(path): continue
    probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        probe_data = json.loads(probe.stdout)
        json.dump(probe_data, open(os.path.join(REPORT_DIR, f"ffprobe_{label.lower()}.json"), "w"), indent=2)
        
        fmt = probe_data.get("format", {})
        vs = [s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"]
        if vs:
            v = vs[0]
            log(f"  {label}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} "
                f"{v.get('r_frame_rate')}fps {float(fmt.get('duration',0)):.1f}s "
                f"{int(fmt.get('size',0)):,} bytes")
    except Exception as e:
        log(f"  {label} probe error: {e}")

# ═══════════════ Thumbnail + Poster ═══════════════
log(f"\nGenerating thumbnail + poster...")
mid_frame = total_frames // 2  # Middle of cinematic
hero_frame = total_frames - int(FPS * 5)  # 5s before end (hero shot)

for name, fn in [("thumbnail", mid_frame), ("poster", hero_frame)]:
    src = os.path.join(FRAMES_DIR, f"frame_{fn:06d}.png")
    dst = os.path.join(IMAGE_DIR, f"{name}.png")
    if os.path.exists(src):
        img = Image.open(src)
        if name == "thumbnail":
            img = img.resize((320, 180))
        img.save(dst, "PNG")
        record_artifact(f"{name}.png", "Image", ".png", dst, "image/png")
        log(f"  {name}: {dst}")

# ═══════════════ Record artifacts ═══════════════
for name, path, mime in [
    ("luxury_cinematic.mp4", mp4_path, "video/mp4"),
    ("luxury_cinematic.webm", webm_path, "video/webm"),
]:
    if os.path.exists(path):
        record_artifact(name, "Video", os.path.splitext(name)[1], path, mime)

for name, path in [
    ("scene_timeline.json", os.path.join(REPORT_DIR, "scene_timeline.json")),
    ("ffprobe_mp4.json", os.path.join(REPORT_DIR, "ffprobe_mp4.json")),
    ("ffprobe_webm.json", os.path.join(REPORT_DIR, "ffprobe_webm.json")),
    ("rendering.log", os.path.join(LOG_DIR, "rendering.log")),
]:
    if os.path.exists(path):
        record_artifact(name, "Report", ".json" if name.endswith("json") else ".log", path, "application/json" if name.endswith("json") else "text/plain")

# Manifest
manifest = {
    "mission": "V5D-2.0-CINEMATIC-VIDEO-EXPORT-001",
    "source_spec_hash": spec_hash, "source_html": SOURCE_HTML, "source_html_hash": html_hash,
    "resolution": list(RESOLUTION), "fps": FPS, "total_frames": total_frames,
    "expected_duration_s": total_s, "render_time_s": render_time,
    "frames_rendered": frames_rendered, "scene_count": len(scenes),
    "mp4_path": mp4_path, "webm_path": webm_path,
    "mp4_size": os.path.getsize(mp4_path) if mp4_ok else 0,
    "webm_size": os.path.getsize(webm_path) if webm_ok else 0,
    "artifacts": ARTIFACTS,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
json.dump(manifest, open(os.path.join(REPORT_DIR, "artifact_manifest.json"), "w"), indent=2, default=str)

# ═══════════════ Storage tree ═══════════════
tree = f"""
storage/
└── projects/
    └── cinematic_v2/
        ├── video/
        │   ├── luxury_cinematic.mp4  ({manifest['mp4_size']:,} bytes)
        │   └── luxury_cinematic.webm ({manifest['webm_size']:,} bytes)
        ├── images/
        │   ├── thumbnail.png
        │   └── poster.png
        ├── reports/
        │   ├── scene_timeline.json
        │   ├── ffprobe_mp4.json
        │   ├── ffprobe_webm.json
        │   └── artifact_manifest.json
        └── logs/
            └── rendering.log
"""
with open(os.path.join(OUTPUT_DIR, "storage_tree.txt"), "w") as f:
    f.write(tree)

log(f"\n{'='*60}")
log(f"RENDER COMPLETE")
log(f"  MP4: {mp4_path} ({manifest['mp4_size']:,} bytes)")
log(f"  WebM: {webm_path} ({manifest['webm_size']:,} bytes)")
log(f"  Frames: {frames_rendered}/{total_frames}")
log(f"  Artifacts: {len(ARTIFACTS)}")
log(f"{tree}")
log(f"{'='*60}")

# Cleanup frames (keep if debugging)
# shutil.rmtree(FRAMES_DIR)

print(f"\n✅ MP4: {mp4_path}")
print(f"✅ WebM: {webm_path}")
print(f"📁 Evidence: {REPORT_DIR}")
