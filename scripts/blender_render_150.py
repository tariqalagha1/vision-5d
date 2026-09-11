import bpy, os, json, math, time, glob, hashlib

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\authoritative_living_room.glb"
RENDER_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\frames\preview"
OUT_JSON = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\blender_preview_result.json"

os.makedirs(RENDER_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

scene = bpy.context.scene

bpy.ops.object.camera_add(location=(10, -10, 5))
cam = bpy.context.object; cam.name = 'CinematicCamera'; scene.camera = cam

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(2.5, 3.0, 1.5))
target = bpy.context.object
track = cam.constraints.new(type='TRACK_TO')
track.target = target; track.track_axis = 'TRACK_NEGATIVE_Z'; track.up_axis = 'UP_Y'

FRAMES = 10
scene.frame_start = 1; scene.frame_end = FRAMES

for frame in range(1, FRAMES + 1):
    t = (frame - 1) / (FRAMES - 1) if FRAMES > 1 else 0
    a = math.pi * 2 * 0.3 * t; r = 9.0
    cx, cy = 2.5, 3.0
    cam.location = (cx + r * math.cos(a), cy - r * math.sin(a), 3.5 + 1.5 * math.sin(t * math.pi))
    cam.keyframe_insert(data_path='location', frame=frame)

bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
bpy.context.object.data.energy = 4.0
bpy.ops.object.light_add(type='AREA', location=(2.5, 3, 2.8))
bpy.context.object.data.energy = 300; bpy.context.object.data.size = 5

scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 1
scene.render.resolution_x = 1280; scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = os.path.join(RENDER_DIR, 'frame_')

print(f'Rendering {FRAMES} frames (Cycles, 1 sample)...')
t0 = time.time()
bpy.ops.render.render(animation=True)
elapsed = time.time() - t0

pngs = sorted(glob.glob(os.path.join(RENDER_DIR, 'frame_*.png')))
sizes = [os.path.getsize(p) for p in pngs] if pngs else []

result = {
    'engine': 'CYCLES', 'samples': 1,
    'expected_frames': FRAMES, 'actual_frames': len(pngs),
    'render_duration_s': round(elapsed, 1),
    'first_frame_size': sizes[0] if sizes else 0,
    'total_size': sum(sizes),
}

with open(OUT_JSON, 'w') as f:
    json.dump(result, f, indent=2)
print('DONE: ' + json.dumps(result))
