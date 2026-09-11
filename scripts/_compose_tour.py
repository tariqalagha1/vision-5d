#!/usr/bin/env python3
"""Compose rendered tour frames into one MP4 (sequential-rename approach)."""
import os, glob, subprocess, hashlib, json, shutil

OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
FRAMES = os.path.join(OUT, "frames")
SEQ = os.path.join(OUT, "seq")
MP4 = os.path.join(OUT, "RE-SingDetch-FH_AS_tour.mp4")
FPS = 30

frames = sorted(glob.glob(os.path.join(FRAMES, "*.png")))
print("frames:", len(frames))
if not frames:
    raise SystemExit("NO FRAMES")

if os.path.exists(SEQ):
    shutil.rmtree(SEQ)
os.makedirs(SEQ)
for i, fr in enumerate(frames):
    shutil.copy2(fr, os.path.join(SEQ, f"frame_{i:04d}.png"))

ffmpeg = "ffmpeg"
cmd = [ffmpeg, "-y", "-framerate", str(FPS), "-i",
       os.path.join(SEQ, "frame_%04d.png"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
       MP4]
r = subprocess.run(cmd, capture_output=True, text=True)
print("ffmpeg exit", r.returncode)
if r.returncode != 0:
    print("STDERR:", r.stderr[-2000:])
    raise SystemExit("FFMPEG FAILED")

size = os.path.getsize(MP4)
sha = hashlib.sha256(open(MP4, "rb").read()).hexdigest()
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
    "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames",
    "-of", "json", MP4], capture_output=True, text=True)
print("probe:", probe.stdout)
print(f"MP4 size={size} sha256={sha}")
print(f"MP4={MP4}")
json.dump({"mp4": MP4, "size": size, "sha256": sha, "fps": FPS,
           "frames": len(frames), "probe": json.loads(probe.stdout)},
          open(os.path.join(OUT, "mp4_info.json"), "w"), indent=2)
print("DONE mp4_info.json")
