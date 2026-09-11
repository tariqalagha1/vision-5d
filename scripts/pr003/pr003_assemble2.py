"""PR003 v2 assembly — encode each shot, crossfade-chain into one tour MP4."""
import os, subprocess, sys, json

OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"
FPS = 24
FADE = 0.5  # crossfade seconds

SHOT_ORDER = ["shot_01", "shot_02", "shot_03", "shot_04", "shot_05", "shot_06"]
# expected frame counts (v2 plan)
EXPECTED = {"shot_01": 72, "shot_02": 60, "shot_03": 72, "shot_04": 72, "shot_05": 60, "shot_06": 84}

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None

# 1. encode each shot
clips = []
for sid in SHOT_ORDER:
    framedir = os.path.join(OUT_DIR, "shots", sid)
    frames = sorted(f for f in os.listdir(framedir) if f.startswith("frame_") and f.endswith(".png"))
    if not frames:
        print(f"{sid}: NO FRAMES — abort")
        sys.exit(1)
    # verify contiguous
    idxs = [int(f[6:10]) for f in frames]
    if idxs != list(range(1, len(frames) + 1)):
        print(f"{sid}: WARNING non-contiguous frames {min(idxs)}..{max(idxs)} (n={len(frames)})")
    exp = EXPECTED[sid]
    if len(frames) < exp:
        print(f"{sid}: WARNING {len(frames)} < expected {exp}")
    clip = os.path.join(OUT_DIR, f"{sid}.mp4")
    r = run(["ffmpeg", "-y", "-framerate", str(FPS),
             "-i", os.path.join(framedir, "frame_%04d.png"),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
             "-movflags", "+faststart", clip])
    if r.returncode != 0:
        print(f"{sid} encode FAILED: {r.stderr[-800:]}")
        sys.exit(1)
    clips.append(clip)
    print(f"{sid}: {len(frames)} frames -> {clip}")

# 2. actual durations
durs = {}
for sid, clip in zip(SHOT_ORDER, clips):
    d = probe_dur(clip)
    if d is None:
        print(f"{sid}: ffprobe failed"); sys.exit(1)
    durs[sid] = d
    print(f"{sid}: duration={d:.3f}s")

# 3. build xfade chain
inputs = []
for c in clips:
    inputs += ["-i", c]

# offset for clip i (1-based): sum of durations before it, minus fade * i
# xfade offset = timestamp in the running output where the transition starts
cum = 0.0
offsets = []
for i, sid in enumerate(SHOT_ORDER):
    if i == 0:
        cum = durs[sid]
        continue
    offsets.append(round(cum - FADE, 4))
    cum = cum + durs[sid] - FADE
total = cum
print("offsets:", offsets, "total:", round(total, 3))

fc = []
prev = "[0:v]"
for i in range(1, len(clips)):
    label = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
    fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offsets[i-1]}{label}")
    prev = f"[v{i}]"
filter_complex = ";".join(fc)

final = os.path.join(OUT_DIR, "pr003_property_tour.mp4")
cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex,
       "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       "-crf", "20", "-movflags", "+faststart", final]
print("ffmpeg assemble...")
r = run(cmd)
if r.returncode != 0:
    print("ASSEMBLE FAILED:", r.stderr[-1500:])
    sys.exit(1)

# 4. probe final
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,duration",
    "-show_entries", "format=duration,size", "-of", "json", final],
    capture_output=True, text=True)
print("final probe:", probe.stdout)
print(f"FINAL TOUR: {final} ({os.path.getsize(final)} bytes, ~{total:.2f}s)")
