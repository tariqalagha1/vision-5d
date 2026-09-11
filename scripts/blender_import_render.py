import bpy, os, json, hashlib

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\authoritative_living_room.glb"
BLEND_OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\authoritative_scene.blend"
RENDER_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\frames"
OUT_JSON = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\blender_result.json"

# Clear and import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

obs = bpy.data.objects
meshes = bpy.data.meshes
mats = bpy.data.materials
print(f'Imported: {len(obs)} objects, {len(meshes)} meshes, {len(mats)} materials')

for ob in obs:
    if ob.type == 'MESH':
        bbox = [ob.matrix_world @ v.co for v in ob.data.vertices]
        xs = [v.x for v in bbox]; ys = [v.y for v in bbox]; zs = [v.z for v in bbox]
        print(f'  {ob.name}: verts={len(ob.data.vertices)} bounds=[{min(xs):.1f},{max(xs):.1f}][{min(ys):.1f},{max(ys):.1f}][{min(zs):.1f},{max(zs):.1f}]')

# Camera
bpy.ops.object.camera_add(location=(8, -8, 4))
cam = bpy.context.object
cam.name = 'CinematicCamera'
cam.rotation_euler = (1.1, 0, 0.7)
bpy.context.scene.camera = cam

# Lights
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
bpy.context.object.data.energy = 3.0
bpy.context.object.data.angle = 0.5

bpy.ops.object.light_add(type='AREA', location=(3, 0, 2.5))
bpy.context.object.data.energy = 200
bpy.context.object.data.size = 4

# Render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'CPU'
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = 'PNG'

# Diagnostic frame
os.makedirs(RENDER_DIR, exist_ok=True)
bpy.context.scene.render.filepath = os.path.join(RENDER_DIR, 'diagnostic_frame.png')
bpy.ops.render.render(write_still=True)

# Save .blend
os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

# Result
with open(GLB_PATH, 'rb') as f:
    glb_sha = hashlib.sha256(f.read()).hexdigest()

result = {
    'glb_sha256': glb_sha,
    'objects': len(obs),
    'meshes': len(meshes),
    'materials': len(mats),
    'blend_saved': BLEND_OUT,
    'diagnostic_frame': os.path.join(RENDER_DIR, 'diagnostic_frame.png')
}

with open(OUT_JSON, 'w') as f:
    json.dump(result, f, indent=2)

print('DONE: ' + json.dumps(result))
