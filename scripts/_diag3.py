"""Final render attempt: override materials to bright, explicit camera, verify visibility."""
import bpy, os, math
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\apps\web\RE-SingDetch-FH_AS.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)
bpy.ops.import_scene.gltf(filepath=GLB)

# override all materials to a bright color
bright = bpy.data.materials.new('Bright'); bright.use_nodes=True
bright.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.75, 0.5, 1)
bright.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.data.materials.clear()
        o.data.materials.append(bright)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=32
scene.render.resolution_x=1280; scene.render.resolution_y=720
scene.render.image_settings.file_format='PNG'

# strong sun
sun = bpy.data.lights.new('Sun','SUN'); sun.energy=8
so=bpy.data.objects.new('Sun',sun); scene.collection.objects.link(so)
so.location=(5000,5000,8000); so.rotation_euler=(math.radians(45),0,math.radians(30))

# bounds
xs=[];ys=[];zs=[]
for o in scene.objects:
    if o.type=='MESH':
        for v in o.data.vertices:
            w=o.matrix_world@v.co; xs.append(w.x); ys.append(w.y); zs.append(w.z)
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
extent=max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))

# camera: top-down, far, looking down
cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=20
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=Vector((cx, cy, cz+extent*3))
cam.rotation_euler=(0,0,0)
print(f"CAMERA at ({cam.location.x:.0f},{cam.location.y:.0f},{cam.location.z:.0f}) looking down, extent={extent:.0f}")
print(f"scene.camera={scene.camera.name}")
scene.render.filepath=os.path.join(OUT,'diag_bright.png')
bpy.ops.render.render(write_still=True)
print("BRIGHT RENDER DONE")
