"""PR002 Phase 6 — Encode MP4 + verify. Run after frames are rendered."""
import os, subprocess, json, sys
from PIL import Image

OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
FRAMES = os.path.join(OUT_DIR, "frames")
MP4 = os.path.join(OUT_DIR, "pr002_first_video.mp4")
FPS = 24

# 1. Count frames
frames = sorted(f for f in os.listdir(FRAMES) if f.endswith(".png"))
print(f"frames on disk: {len(frames)}")

# 2. Encode MP4
cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAMES, "frame_%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
    "-movflags", "+faststart",
    MP4,
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("ffmpeg exit:", r.returncode)
if r.returncode != 0:
    print("STDERR:", r.stderr[-2000:])
    sys.exit(1)

# 3. ffprobe metadata
probe = subprocess.run([
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,duration",
    "-show_entries", "format=duration,size",
    "-of", "json", MP4,
], capture_output=True, text=True)
meta = json.loads(probe.stdout)
print("probe:", json.dumps(meta, indent=2))

# 4. Black-frame / content check: extract N frames from MP4 and measure
check_dir = os.path.join(OUT_DIR, "mp4_checks")
os.makedirs(check_dir, exist_ok=True)
n_checks = 6
total_frames = int(meta["streams"][0].get("nb_frames", 120))
indices = [1 + int(i * (total_frames - 1) / (n_checks - 1)) for i in range(n_checks)]
stats = []
for idx in indices:
    out = os.path.join(check_dir, f"check_{idx:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-i", MP4, "-vf", f"select=eq(n\\,{idx-1})", "-vframes", "1", out],
                   capture_output=True, text=True)
    if os.path.exists(out):
        im = Image.open(out).convert("RGB")
        px = list(im.getdata()); n = len(px)
        lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in px]
        mean = sum(lum)/n; std = (sum((x-mean)**2 for x in lum)/n)**0.5
        mn = min(lum)
        stats.append({"frame": idx, "mean": round(mean,1), "std": round(std,1), "min": round(mn,1)})

print("MP4 frame content stats:")
for s in stats:
    print(f"  frame {s['frame']:4d}: mean={s['mean']:6.1f} std={s['std']:5.1f} min={s['min']:5.1f}")

# black = mean < 15
blacks = [s for s in stats if s["mean"] < 15]
print(f"black frames detected (mean<15): {len(blacks)} / {len(stats)}")

# size
size = os.path.getsize(MP4)
print(f"MP4 size: {size} bytes")
print(f"MP4 path: {MP4}")
