#!/usr/bin/env python3
"""Generate full-length cinematic video for RE-SingDetch-FH_AS"""
import os, sys, json, time, math, subprocess, tempfile, hashlib
sys.path.insert(0, '.')
from PIL import Image, ImageDraw, ImageFont

OUT = 'output/RE-SingDetch-FH_AS'
RES = (1920, 1080); FPS = 30

with open(os.path.join(OUT,'cinematic/storyboard.json')) as f: sb = json.load(f)
SCENES = sb['scenes']; total_s = sb['total_s']; total_frames = int(total_s * FPS)
print(f'Scenes: {len(SCENES)}  Duration: {total_s}s  Frames: {total_frames}')

with open(os.path.join(OUT,'design/ai_design.v5d.json')) as f: design = json.load(f)
furniture = design['furniture']

frames_dir = tempfile.mkdtemp(prefix='v5dvideo_')
t0 = time.time()

for fi in range(total_frames):
    elapsed = fi / FPS
    cum = 0; si = 0
    for i, s in enumerate(SCENES):
        if elapsed < cum + s['d']:
            si = i
            break
        cum += s['d']
    else:
        si = len(SCENES) - 1
    
    scene_t = (elapsed - cum) / max(SCENES[si]['d'], 0.1)
    sn = SCENES[si]
    
    img = Image.new('RGB', RES, (13, 17, 23))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, int(RES[1]*0.55), RES[0], RES[1]], fill=(26, 26, 46))
    
    # Grid
    for gx in range(-15, 16, 4):
        for gz in range(-12, 13, 4):
            px = int((gx + 15) * RES[0] / 30)
            py = int(RES[1]*0.55 + gz * RES[1]*0.04)
            if 0 <= px < RES[0] and 0 <= py < RES[1]:
                draw.point((px, py), fill=(33, 38, 45))
    
    # Furniture
    for f in furniture[:20]:
        px = int((f['pos'][0] + 15) * RES[0] / 30)
        py = int(RES[1]*0.55 - (f['pos'][2] + 8) * RES[1] / 20)
        w = max(2, int(f['dims'][0] * RES[0] / 30))
        h = max(2, int(f['dims'][2] * RES[1] / 20))
        c = tuple(int(f['color'][i:i+2], 16) for i in (1, 3, 5))
        draw.rectangle([max(0, px-w), max(0, py-h), min(RES[0], px+w), min(RES[1], py+h)], fill=c)
        try:
            font = ImageFont.truetype('arial.ttf', 8)
        except:
            font = ImageFont.load_default()
        draw.text((px-w, py-h-8), f['label'][:8], fill=(255, 255, 255), font=font)
    
    # Overlays
    for ov in sn.get('o', []):
        appear_ms = (ov.get('a', 0)) * 1000
        if scene_t * sn['d'] * 1000 >= appear_ms:
            try:
                font = ImageFont.truetype('arial.ttf', 48 if ov.get('s') == 'title' else 16)
            except:
                font = ImageFont.load_default()
            y = int(RES[1]*0.1) if ov.get('s') == 'title' else int(RES[1]*0.88)
            cs = ov.get('c', '#FFF')
            try:
                ct = tuple(int(cs[i:i+2], 16) for i in (1, 3, 5))
            except:
                ct = (255, 255, 255)
            draw.text((RES[0]//2 - 150, y), ov['t'], fill=ct, font=font)
    
    img.save(os.path.join(frames_dir, f'frame_{fi:06d}.png'), 'PNG')
    if fi % 500 == 0:
        elapsed_t = time.time() - t0
        rate = (fi + 1) / max(elapsed_t, 0.001)
        print(f'  Frame {fi}/{total_frames} ({fi*100/total_frames:.0f}%) — {rate:.1f} fps')

render_time = time.time() - t0
print(f'Rendered {total_frames} frames in {render_time:.0f}s ({total_frames/render_time:.1f} fps)')

# MP4
mp4_path = os.path.join(OUT, 'cinematic', 'RE-SingDetch-FH_AS.mp4')
subprocess.run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', os.path.join(frames_dir, 'frame_%06d.png'),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4_path],
    capture_output=True, timeout=300)
mp4_size = os.path.getsize(mp4_path)

# WebM
webm_path = os.path.join(OUT, 'cinematic', 'RE-SingDetch-FH_AS.webm')
subprocess.run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', os.path.join(frames_dir, 'frame_%06d.png'),
    '-c:v', 'libvpx-vp9', '-b:v', '1M', '-deadline', 'realtime', webm_path],
    capture_output=True, timeout=300)
webm_size = os.path.getsize(webm_path)

# GIF
gif_path = os.path.join(OUT, 'cinematic', 'preview.gif')
subprocess.run(['ffmpeg', '-y', '-framerate', '5', '-i', os.path.join(frames_dir, 'frame_%06d.png'),
    '-vf', 'scale=480:-1', '-t', '15', gif_path], capture_output=True, timeout=60)

# Thumbnail
mid = total_frames // 2
sf = os.path.join(frames_dir, f'frame_{mid:06d}.png')
if os.path.exists(sf):
    Image.open(sf).resize((320, 180)).save(os.path.join(OUT, 'cinematic', 'thumbnail.png'), 'PNG')

# Verify
probe = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_path],
    capture_output=True, text=True, timeout=15)
pd = json.loads(probe.stdout)
vs = [s for s in pd.get('streams', []) if s.get('codec_type') == 'video']
v = vs[0] if vs else {}
dur = float(pd.get('format', {}).get('duration', 0))
mp4_sha = hashlib.sha256(open(mp4_path, 'rb').read()).hexdigest()
webm_sha = hashlib.sha256(open(webm_path, 'rb').read()).hexdigest()

print(f'\n{"="*60}')
print(f'VIDEO RENDER COMPLETE')
print(f'{"="*60}')
print(f'  MP4:  {v.get("width")}x{v.get("height")} {v.get("codec_name")} {v.get("r_frame_rate")}fps {dur:.1f}s {mp4_size:,}B')
print(f'  SHA-256: {mp4_sha[:32]}...')
print(f'  WebM: {webm_size:,}B  SHA-256: {webm_sha[:16]}...')
print(f'  GIF:  {os.path.getsize(gif_path):,}B')
print(f'  Path: {mp4_path}')

import shutil
shutil.rmtree(frames_dir, ignore_errors=True)
