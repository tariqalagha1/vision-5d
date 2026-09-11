"""Isolate: does a simple cube render in this Blender setup?"""
import bpy, os, math
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

# simple cube
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0,0,1000))
cube = bpy.context.object
mat = bpy.data.materials.new('Red'); mat.use_nodes=True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1,0,0,1)
cube.data.materials.append(mat)

scene = bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16
scene.render.resolution_x=640; scene.render.resolution_y=360
scene.render.image_settings.file_format='PNG'

sun = bpy.data.lights.new('Sun','SUN'); sun.energy=5
so=bpy.data.objects.new('Sun',sun); scene.collection.objects.link(so)
so.location=(3000,3000,5000); so.rotation_euler=(math.radians(40),0,math.radians(30))

cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=35
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=(3000,-3000,3000); cam.rotation_euler=(math.radians(60),0,math.radians(45))

scene.render.filepath=os.path.join(OUT,'cube_test.png')
bpy.ops.render.render(write_still=True)
print("CUBE TEST DONE")
