"""Emission cube test — no lighting needed."""
import bpy, os
from mathutils import Vector
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0,0,1000))
cube = bpy.context.object
mat = bpy.data.materials.new('Em'); mat.use_nodes=True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
if bsdf is None:
    # create it
    mat.node_tree.nodes.clear()
    bsdf = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], mat.node_tree.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
bsdf.inputs['Base Color'].default_value = (1,0,0,1)
bsdf.inputs['Emission'].default_value = (1,0,0,1)
bsdf.inputs['Emission Strength'].default_value = 5.0
cube.data.materials.append(mat)

scene = bpy.context.scene
scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=8
scene.render.resolution_x=640; scene.render.resolution_y=360
scene.render.image_settings.file_format='PNG'

cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=35
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=Vector((0,-6000,3000))
d = Vector((0,0,1000)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

scene.render.filepath=os.path.join(OUT,'cube_emission.png')
bpy.ops.render.render(write_still=True)
print("EMISSION TEST DONE")
