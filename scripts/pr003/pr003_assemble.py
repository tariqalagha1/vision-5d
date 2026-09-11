"""PR003 Phase 9-11 — encode each shot to a clip, crossfade-chain into one tour MP4."""
import os, subprocess, json, sys

OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"
FPS = 24
FADE = 0.5  # crossfade seconds between shots

SHOT_ORDER = ["shot_01", "shot_02", "shot_03", "shot_04", "shot_05", "shot_06"]
DURATIONS = {"shot_01": 3.0, "shot_02": 2.5, "shot_03": 2.5, "shot_04": 3.0, "shot_05": 2.0, "shot_06": 3.0}

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r

# 1. Encode each shot to a clip
clips = []
for sid in SHOT_ORDER:
    framedir = os.path.join(OUT_DIR, "shots", sid)
    frames = sorted(f for f in os.listdir(framedir) if f.endswith(".png"))
    if not frames:
        print(f"{sid}: NO FRAMES — abort")
        sys.exit(1)
    clip = os.path.join(OUT_DIR, f"{sid}.mp4")
    r = run(["ffmpeg", "-y", "-framerate", str(FPS),
             "-i", os.path.join(framedir, "frame_%04d.png"),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
             "-movflags", "+faststart", clip])
    if r.returncode != 0:
        print(f"{sid} encode FAILED:", r.stderr[-800:])
        sys.exit(1)
    clips.append(clip)
    print(f"{sid}: {len(frames)} frames -> {clip}")

# 2. Build xfade filter chain with programmatic offsets
# offsets: each xfade offset = cumulative duration so far - FADE
cum = 0.0
offsets = []
for i, sid in enumerate(SHOT_ORDER):
    if i == 0:
        cum += DURATIONS[sid]
        continue
    offsets.append(round(cum - FADE, 3))
    cum = cum + DURATIONS[sid] - FADE

total_duration = cum
print("offsets:", offsets, "total_duration:", total_duration)

# build filter_complex
inputs = []
for c in clips:
    inputs += ["-i", c]

fc_parts = []
prev = "[0:v]"
for i in range(1, len(clips)):
    out_label = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
    fc_parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offsets[i-1]}{out_label}")
    prev = f"[v{i}]"

filter_complex = ";".join(fc_parts)

final = os.path.join(OUT_DIR, "pr003_property_tour.mp4")
cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex,
       "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       "-crf", "20", "-movflags", "+faststart", final]
print("ffmpeg:", " ".join(cmd))
r = run(cmd)
if r.returncode != 0:
    print("ASSEMBLE FAILED:", r.stderr[-1500:])
    sys.exit(1)

# 3. Probe final
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,duration",
    "-show_entries", "format=duration,size", "-of", "json", final],
    capture_output=True, text=True)
print("final probe:", probe.stdout)
size = os.path.getsize(final)
print(f"FINAL TOUR: {final} ({size} bytes, ~{total_duration}s)")
