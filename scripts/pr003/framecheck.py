import os
from PIL import Image

base = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003\shots"

def analyze(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    n = w * h
    tot_lum = 0.0
    min_l = 255; max_l = 0
    # sofa = blue-gray: B clearly > R (blue-dominant, mid-dark)
    # table = dark wood: R > G > B, low value
    # floor = warm wood: R > B, mid value, orange-ish (R high, B low)
    sofa_px = []; table_px = []; floor_px = []; wall_px = []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            lum = 0.299*r + 0.587*g + 0.114*b
            tot_lum += lum
            if lum < min_l: min_l = lum
            if lum > max_l: max_l = lum
            if b > r + 8 and b > 40:  # blue-dominant (sofa)
                sofa_px.append((x, y))
            elif r > g + 8 and g > b + 5 and r < 140:  # dark wood (table)
                table_px.append((x, y))
            elif r > b + 15 and r > 90 and r < 200 and b < 120:  # warm wood floor
                floor_px.append((x, y))
            elif r > 200 and g > 200 and b > 195:  # off-white wall
                wall_px.append((x, y))
    mean = tot_lum / (n / 4)
    def bbox(pts):
        if not pts: return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    def frac(pts): return len(pts) / (n / 4)
    print(f"{os.path.basename(path)}: size={w}x{h} meanLum={mean:.1f} min={min_l} max={max_l}")
    print(f"   sofa(blue) frac={frac(sofa_px):.3f} bbox={bbox(sofa_px)}")
    print(f"   table(dark) frac={frac(table_px):.3f} bbox={bbox(table_px)}")
    print(f"   floor(warm) frac={frac(floor_px):.3f} bbox={bbox(floor_px)}")
    print(f"   wall(white) frac={frac(wall_px):.3f} bbox={bbox(wall_px)}")

for i in range(1, 7):
    p = os.path.join(base, f"shot_0{i}", f"mid_shot_0{i}.png")
    if os.path.exists(p):
        analyze(p)
    else:
        print(f"shot_0{i}: MISSING mid frame")
