import bpy, mathutils, math, os
GLB = r"C:/Users/admin/workspaces/vision-5d/.exports/2f4475ad-7ab9-4a00-bb8e-79713f7773cb.glb"
OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=GLB)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
wall=[]; hide=[]
for o in meshes:
    if o.name.split('.')[0]=='wall_solid': wall.append(o)
    else: hide.append(o)
for o in hide: o.hide_render=True; o.hide_viewport=True
bpy.context.view_layer.update()
def bounds(objs):
    allc=[(o.matrix_world@mathutils.Vector(c)) for o in objs for c in o.bound_box]
    return [min(v[i] for v in allc) for i in range(3)],[max(v[i] for v in allc) for i in range(3)]
mn,mx=bounds(wall); ext=[mx[i]-mn[i] for i in range(3)]
cx,cy,cz=[(mn[i]+mx[i])/2 for i in range(3)]; W,L,H=ext[0],ext[1],ext[2]
bpy.ops.mesh.primitive_plane_add(size=1, location=(cx,cy,0))
floor=bpy.context.active_object; floor.scale=(W*1.15/2,L*1.15/2,1.0); floor.color=(0.86,0.86,0.88,1)
for o in wall: o.color=(0.62,0.46,0.33,1)
cam_data=bpy.data.cameras.new("C"); cam_data.lens=24; cam_data.clip_end=200000
cam=bpy.data.objects.new("C",cam_data); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera=cam
cam.location=(cx+W*1.1, cy+L*0.95, H*3.6)
tgt=mathutils.Vector((cx,cy,H*0.1)); cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
nt=w.node_tree; nt.nodes["Background"].inputs[0].default_value=(0.96,0.96,0.97,1); nt.nodes["Background"].inputs[1].default_value=1.0
sun=bpy.data.lights.new("S",'SUN'); sun.energy=3.0
so=bpy.data.objects.new("S",sun); bpy.context.scene.collection.objects.link(so)
so.rotation_euler=(math.radians(60),math.radians(25),math.radians(18))
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'
sc.display.shading.light='STUDIO'
sc.display.shading.color_type='OBJECT'
sc.render.resolution_x=960; sc.render.resolution_y=540
sc.render.image_settings.file_format='PNG'
bpy.context.view_layer.update()
sc.render.filepath=OUT+"/overview_v5.png"
bpy.ops.render.render(write_still=True)
print("DONE overview_v5.png")
