import hashlib, os, glob
from PIL import Image
import numpy as np

base = r'C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001'

mp4 = os.path.join(base, 'final_authoritative_render.mp4')
print('MP4 SHA-256:', hashlib.sha256(open(mp4,'rb').read()).hexdigest())
print('MP4 size:', os.path.getsize(mp4), 'bytes')
print()

frames_dir = os.path.join(base, 'final_render')
pngs = sorted(glob.glob(os.path.join(frames_dir, 'frame_*.png')))
print(f'Frames: {len(pngs)}')

for fn in [pngs[0], pngs[len(pngs)//2], pngs[-1]]:
    img = Image.open(fn)
    arr = np.array(img.convert('RGB'))
    print(f'  {os.path.basename(fn)}: mean={arr.mean():.0f} std={arr.std():.0f} size={os.path.getsize(fn)}')
