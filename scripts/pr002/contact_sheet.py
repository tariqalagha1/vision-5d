"""PR002 — build a 4x3 contact sheet from the MP4 for visual review."""
import subprocess, os
from PIL import Image

OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
MP4 = os.path.join(OUT_DIR, "pr002_first_video.mp4")
SHEET = os.path.join(OUT_DIR, "contact_sheet.png")

n = 12  # 4x3
total = 120
indices = [1 + int(i * (total - 1) / (n - 1)) for i in range(n)]

tmp = os.path.join(OUT_DIR, "sheet_tmp")
os.makedirs(tmp, exist_ok=True)
thumbs = []
for idx in indices:
    out = os.path.join(tmp, f"s_{idx:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-i", MP4, "-vf", f"select=eq(n\\,{idx-1})",
                    "-vframes", "1", out], capture_output=True, text=True)
    im = Image.open(out).resize((320, 180))
    thumbs.append(im)

cols, rows = 4, 3
W, H = 320, 180
sheet = Image.new("RGB", (cols * W, rows * H), (20, 20, 20))
for i, im in enumerate(thumbs):
    r, c = divmod(i, cols)
    sheet.paste(im, (c * W, r * H))
sheet.save(SHEET)
print("contact sheet:", SHEET)
print("indices:", indices)
