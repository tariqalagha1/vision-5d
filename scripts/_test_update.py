import bpy
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0,0,1000))
scene=bpy.context.scene
cam_data=bpy.data.cameras.new('Cam'); cam_data.lens=35
cam=bpy.data.objects.new('Cam',cam_data); scene.collection.objects.link(cam)
scene.camera=cam
cam.location=Vector((0,-6000,3000))
d = Vector((0,0,1000)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
print("BEFORE update view dir:", tuple(round(x,2) for x in (cam.matrix_world.to_quaternion() @ Vector((0,0,-1)))))
bpy.context.view_layer.update()
print("AFTER update view dir:", tuple(round(x,2) for x in (cam.matrix_world.to_quaternion() @ Vector((0,0,-1)))))
print("rot:", tuple(round(x*57.3,1) for x in cam.rotation_euler))
