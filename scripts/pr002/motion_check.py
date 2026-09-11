"""PR002 — verify camera motion by comparing frames across the video."""
import os
from PIL import Image
import math

FRAMES = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002\frames"
files = sorted(f for f in os.listdir(FRAMES) if f.endswith(".png"))

def downscale_mean(path):
    im = Image.open(os.path.join(FRAMES, path)).convert("L").resize((64, 36))
    return list(im.getdata())

def diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)

# sample frames
indices = [0, 15, 30, 45, 60, 75, 90, 105, 119]
means = {}
for i in indices:
    means[i] = downscale_mean(files[i])

print("Frame-to-frame differences (higher = more motion):")
for k in range(len(indices) - 1):
    i = indices[k]; j = indices[k+1]
    d = diff(means[i], means[j])
    print(f"  frame {i+1:4d} -> {j+1:4d}: mean abs diff = {d:.1f}")

# total: start vs end
d_total = diff(means[0], means[-1])
print(f"\nstart(frame1) vs end(frame120): diff = {d_total:.1f}")

# consecutive frame motion (frame 60 vs 61)
a = downscale_mean(files[59]); b = downscale_mean(files[60])
print(f"consecutive frame 60->61 diff = {diff(a,b):.1f}")
