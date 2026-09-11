"""Minimal diagnostic render: camera straight down at building center."""
import bpy, os, math
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\apps\web\RE-SingDetch-FH_AS.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)
for l in list(bpy.data.lights): bpy.data.lights.remove(l)
for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)

bpy.ops.import_scene.gltf(filepath=GLB)

# count objects
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print("MESH OBJECTS:", len(meshes))
print("MATERIALS:", len(bpy.data.materials))

# bounds
xs=[];ys=[];zs=[]
for o in meshes:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
extent=max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
print(f"CENTER ({cx:.0f},{cy:.0f},{cz:.0f}) EXTENT {extent:.0f}")

scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16
scene.render.resolution_x=960; scene.render.resolution_y=540
scene.render.image_settings.file_format='PNG'

# light
sun = bpy.data.lights.new('Sun','SUN'); sun.energy=5
so=bpy.data.objects.new('Sun',sun); scene.collection.objects.link(so)
so.location=(cx+extent, cy+extent, cz+extent*2)
so.rotation_euler=(math.radians(50),0,math.radians(40))

# camera straight down
cam_data = bpy.data.cameras.new('Cam'); cam_data.lens=35
cam = bpy.data.objects.new('Cam', cam_data); scene.collection.objects.link(cam)
scene.camera = cam
cam.location = Vector((cx, cy, cz + extent*1.5))
cam.rotation_euler = (0,0,0)  # looks down -Z
scene.render.filepath = os.path.join(OUT, 'diag_top.png')
bpy.ops.render.render(write_still=True)
print("DIAG RENDER DONE")
