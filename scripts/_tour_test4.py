import bpy, mathutils, math, os
GLB = r"C:/Users/admin/workspaces/vision-5d/.exports/2f4475ad-7ab9-4a00-bb8e-79713f7773cb.glb"
OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=GLB)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
keep=[]; hide=[]
for o in meshes:
    if o.name.split('.')[0]=='wall_solid': keep.append(o)
    else: hide.append(o)
for o in hide: o.hide_render=True; o.hide_viewport=True
bpy.context.view_layer.update()

def bounds(objs):
    allc=[(o.matrix_world@mathutils.Vector(c)) for o in objs for c in o.bound_box]
    return [min(v[i] for v in allc) for i in range(3)],[max(v[i] for v in allc) for i in range(3)]
mn,mx=bounds(keep); ext=[mx[i]-mn[i] for i in range(3)]
cx,cy,cz=[(mn[i]+mx[i])/2 for i in range(3)]
W,L,H=ext[0],ext[1],ext[2]
print(f"KEEP={len(keep)} HIDE={len(hide)} extent=[{round(W)},{round(L)},{round(H)}]mm = X {W/1000:.1f}m Y {L/1000:.1f}m H {H/1000:.1f}m center={[round(v) for v in (cx,cy,cz)]}")

cam_data=bpy.data.cameras.new("C"); cam_data.lens=24; cam_data.clip_end=200000
cam=bpy.data.objects.new("C",cam_data); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera=cam
cam.location=(cx, cy+L*0.95, H*4.0)
tgt=mathutils.Vector((cx,cy,H*0.1))
cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()

w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
nt=w.node_tree; nt.nodes["Background"].inputs[0].default_value=(0.85,0.88,0.92,1); nt.nodes["Background"].inputs[1].default_value=1.0
sun=bpy.data.lights.new("S",'SUN'); sun.energy=3.5
so=bpy.data.objects.new("S",sun); bpy.context.scene.collection.objects.link(so)
so.rotation_euler=(math.radians(55),math.radians(30),math.radians(20))

sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=960; sc.render.resolution_y=540
sc.render.image_settings.file_format='PNG'
sc.eevee.taa_render_samples=32
bpy.context.view_layer.update()
sc.render.filepath=OUT+"/overview_v4.png"
bpy.ops.render.render(write_still=True)
print("DONE overview_v4.png")
