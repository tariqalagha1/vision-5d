"""Vision 5D — Full Building Render (RE-SingDetch-FH) — CYCLES CPU multi-shot.

Imports the real full-building GLB, frames the camera to bounds, renders a
small set of distinct shots to prove the full building renders, for MP4 assembly.
"""
import bpy, os, math, sys

GLB = r"C:\Users\admin\workspaces\vision-5d\apps\web\RE-SingDetch-FH_AS.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)

RES_X, RES_Y, SAMPLES = 960, 540, 16
FPS = 12
SHOTS = [
    # (name, camera_location, look_at)  — world units (mm)
    ("overview", (1800, 3200, 3400), (1100, 1350, 1300)),
    ("front",    (1100, 1600, 5000),   (1100, 1350, 1300)),
    ("orbit",    (4200, 2600, 2600),   (1100, 1350, 1300)),
]

# ── Reset scene ──
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)

# ── Import GLB ──
bpy.ops.import_scene.gltf(filepath=GLB)
print("GLB imported")

# ── Compute scene bounds ──
xs, ys, zs = [], [], []
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
minx, maxx = min(xs), max(xs)
miny, maxy = min(ys), max(ys)
minz, maxz = min(zs), max(zs)
cx, cy, cz = (minx+maxx)/2, (miny+maxy)/2, (minz+maxz)/2
extent = max(maxx-minx, maxy-miny, maxz-minz)
print(f"Bounds: ({minx:.0f},{miny:.0f},{minz:.0f}) - ({maxx:.0f},{maxy:.0f},{maxz:.0f}) center=({cx:.0f},{cy:.0f},{cz:.0f}) extent={extent:.0f}")

# ── Render engine ──
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'

# ── Lighting ──
sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = 3.0
so = bpy.data.objects.new('Sun', sun); scene.collection.objects.link(so)
so.location = (cx + extent, cy + extent * 1.5, cz + extent)
so.rotation_euler = (math.radians(40), 0, math.radians(35))
area = bpy.data.lights.new('Area', 'AREA'); area.energy = 300; area.size = extent
ao = bpy.data.objects.new('Area', area); scene.collection.objects.link(ao)
ao.location = (cx, cy, cz + extent * 1.2)
ao.rotation_euler = (math.radians(180), 0, 0)

# ── Camera ──
cam_data = bpy.data.cameras.new("Cam"); cam_data.lens = 24; cam_data.clip_end = 200000
cam = bpy.data.objects.new('Cam', cam_data); scene.collection.objects.link(cam)
scene.camera = cam

# Track To constraint — reliable camera aiming
empty = bpy.data.objects.new('TrackTarget', None)
scene.collection.objects.link(empty)
track = cam.constraints.new(type='TRACK_TO')
track.target = empty
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

from mathutils import Vector

frame_idx = 1
d = extent * 2.6
shots = [
    ("top",     (cx, cy, cz + d * 1.6), (cx, cy, cz)),          # top-down overview
    ("overview",(cx + d, cy + d * 0.9, cz + d * 0.7), (cx, cy, cz)),
    ("front",   (cx, cy + d, cz + d * 0.35), (cx, cy, cz)),
]
for name, loc, tgt in shots:
    cam.location = Vector(loc)
    empty.location = Vector(tgt)
    bpy.context.view_layer.update()  # force depsgraph so camera matrix updates
    scene.frame_set(frame_idx)
    scene.render.filepath = os.path.join(OUT, f"frame_{frame_idx:03d}")
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {name} -> frame_{frame_idx:03d}.png")
    frame_idx += 1

# Save .blend
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scene.blend"))
print("RENDER COMPLETE — frames:", frame_idx - 1)
