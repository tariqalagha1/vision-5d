"""Definitive: cube with depsgraph update."""
import bpy, os
from mathutils import Vector
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0,0,1000))
cube=bpy.context.object
mat=bpy.data.materials.new('Red'); mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(1,0,0,1)
cube.data.materials.append(mat)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=640; scene.render.resolution_y=360
scene.render.image_settings.file_format='PNG'
sun=bpy.data.lights.new('Sun','SUN'); sun.energy=8
so=bpy.data.objects.new('Sun',sun); scene.collection.objects.link(so)
so.location=(0,0,8000); so.rotation_euler=(0,0,0)
cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=35
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=Vector((0,-6000,3000))
d=Vector((0,0,1000))-cam.location
cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
print("view dir:", tuple(round(x,2) for x in (cam.matrix_world.to_quaternion() @ Vector((0,0,-1)))))
scene.render.filepath=os.path.join(OUT,'cube_final.png')
bpy.ops.render.render(write_still=True)
print("CUBE FINAL DONE")
