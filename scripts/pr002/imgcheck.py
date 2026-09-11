import os
from PIL import Image
import collections

base = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
p = os.path.join(base, "diagnostic_frame.png")
im = Image.open(p)
print("mode:", im.mode, "size:", im.size, "bits:", getattr(im, "bits", "?"))
im = im.convert("RGB")
px = list(im.getdata())
n = len(px)
lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in px]
mn = min(lum); mx = max(lum)
print(f"minLum={mn:.2f} maxLum={mx:.2f}")

# histogram of luminance (bucket to 8 bins)
bins = [0]*8
for l in lum:
    b = int(l/32)
    if b > 7: b = 7
    bins[b] += 1
print("lum histogram (0-31,32-63,...224-255):", bins)

# unique colors sample
from collections import Counter
cnt = Counter(px)
print("unique colors:", len(cnt))
print("top 5 colors:", cnt.most_common(5))

# center region vs corner
w, h = im.size
center_px = [lum[y*w+x] for y in range(h//2-50, h//2+50) for x in range(w//2-50, w//2+50)]
corner_px = [lum[y*w+x] for y in range(0,100) for x in range(0,100)]
print(f"center meanLum={sum(center_px)/len(center_px):.1f} corner(0,0) meanLum={sum(corner_px)/len(corner_px):.1f}")
