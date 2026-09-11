import os
from PIL import Image

base = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003\shots"
for i in range(1, 7):
    p = os.path.join(base, f"shot_0{i}", f"mid_shot_0{i}.png")
    if not os.path.exists(p):
        print(f"shot_0{i}: MISSING")
        continue
    im = Image.open(p).convert("RGB")
    px = list(im.getdata()); n = len(px)
    lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in px]
    m = sum(lum)/n; s = (sum((x-m)**2 for x in lum)/n)**0.5
    # distinct color bands (to confirm material differentiation)
    rs = set(); gs = set(); bs = set()
    for c in px[:20000]:
        rs.add(c[0]//32); gs.add(c[1]//32); bs.add(c[2]//32)
    print(f"shot_0{i}: mean={m:.1f} std={s:.1f} min={min(lum):.0f} max={max(lum):.0f} colorBands(r,g,b)={len(rs)},{len(gs)},{len(bs)}")
