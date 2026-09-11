import os
from PIL import Image

base = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003\shots"

def analyze(path, label):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    n = (w // 2) * (h // 2)
    tot = 0.0; mn = 255; mx = 0
    sofa = 0; table = 0; sky = 0; wall = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            lum = 0.299*r + 0.587*g + 0.114*b
            tot += lum; mn = min(mn, lum); mx = max(mx, lum)
            # sofa: blue-gray (B > R, mid-dark, not too bright)
            if b > r + 8 and b > 40 and b < 200:
                sofa += 1
            # table: dark wood (R > G > B, low value)
            if r > g + 8 and g > b + 5 and r < 140:
                table += 1
            # sky: bright light-blue (high B AND high R, bright)
            if b > 180 and r > 120 and g > 150 and r < b:
                sky += 1
            # wall: off-white
            if r > 200 and g > 200 and b > 195:
                wall += 1
    print(f"{label}: lum mean={tot/n:.0f} min={mn} max={mx} | sofa={sofa/n:.3f} table={table/n:.3f} sky={sky/n:.3f} wall={wall/n:.3f}")

for i in range(1, 7):
    p = os.path.join(base, f"shot_0{i}", f"mid2_shot_0{i}.png")
    if os.path.exists(p):
        analyze(p, f"mid2_shot_0{i}")
    else:
        print(f"shot_0{i}: MISSING mid2")
