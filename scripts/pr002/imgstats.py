import os
try:
    from PIL import Image
except ImportError:
    print("NO_PIL")
    import sys; sys.exit(0)

base = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
paths = {
    "diagnostic": os.path.join(base, "diagnostic_frame.png"),
    "key_start": os.path.join(base, "keyframes", "keyframe_start_f0001.png"),
    "key_middle": os.path.join(base, "keyframes", "keyframe_middle_f0060.png"),
    "key_end": os.path.join(base, "keyframes", "keyframe_end_f0120.png"),
}
for name, p in paths.items():
    if not os.path.exists(p):
        print(name, "MISSING", p)
        continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    px = list(im.getdata())
    n = len(px)
    r = sum(c[0] for c in px)/n
    g = sum(c[1] for c in px)/n
    b = sum(c[2] for c in px)/n
    lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in px]
    mean_l = sum(lum)/n
    std_l = (sum((x-mean_l)**2 for x in lum)/n)**0.5
    print(f"{name}: size={w}x{h} meanRGB=({r:.1f},{g:.1f},{b:.1f}) meanLum={mean_l:.1f} stdLum={std_l:.1f}")
