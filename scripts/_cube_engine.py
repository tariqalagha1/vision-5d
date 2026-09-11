"""Clean cube test: EEVEE vs CYCLES, red material."""
import bpy, os, sys
from mathutils import Vector
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)
ENGINE = sys.argv[-1] if len(sys.argv) > 1 else 'EEVEE'

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0,0,1000))
cube = bpy.context.object
mat = bpy.data.materials.new('Red'); mat.use_nodes=True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (1,0,0,1)
cube.data.materials.append(mat)

scene = bpy.context.scene
if ENGINE == 'CYCLES':
    scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16
else:
    scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=16
scene.render.resolution_x=640; scene.render.resolution_y=360
scene.render.image_settings.file_format='PNG'

sun = bpy.data.lights.new('Sun','SUN'); sun.energy=5
so=bpy.data.objects.new('Sun',sun); scene.collection.objects.link(so)
so.location=(3000,3000,5000); so.rotation_euler=(1.0,0,0.8)

cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=35
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=Vector((0,-6000,3000))
d = Vector((0,0,1000)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

scene.render.filepath=os.path.join(OUT,f'cube_{ENGINE}.png')
bpy.ops.render.render(write_still=True)
print(f"CUBE {ENGINE} DONE")
