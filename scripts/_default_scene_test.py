import bpy, os
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\runs\vision5d-final-certification-repair-001\render_frames"
os.makedirs(OUT, exist_ok=True)
# do NOT delete anything — render the default startup scene (cube + light + camera)
scene = bpy.context.scene
print("default objects:", [(o.name, o.type) for o in scene.objects])
print("default camera:", scene.camera)
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=640; scene.render.resolution_y=360
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(OUT,'default_scene.png')
bpy.ops.render.render(write_still=True)
print("DEFAULT SCENE DONE")
