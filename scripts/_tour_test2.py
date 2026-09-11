import bpy, mathutils, math, os

GLB = r"C:/Users/admin/workspaces/vision-5d/.exports/96d13d7a-172a-45c2-8746-dad1bf5226f8.glb"
OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
os.makedirs(OUT, exist_ok=True)

# SCALE_MATERIAL_FOR_TOUR fix: 1 DXF unit = 1 foot = 304.8 mm
# scene wall X extent 1166mm -> 40.1 units (29.08 mm/u) ; wall Y(footprint) 1955mm -> 80.19 units (24.38 mm/u)
SX = 304.8 / 29.08   # ~10.48
SY = 304.8 / 24.38   # ~12.50

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

def center(o):
    cs=[o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    return tuple(sum(v[i] for v in cs)/len(cs) for i in range(3))

wall_objs=[]; door_objs=[]
for o in meshes:
    c=center(o)
    if abs(c[0]) < 200 and abs(c[1]) < 200:
        door_objs.append(o)
    else:
        wall_objs.append(o)

for o in door_objs:
    o.hide_render=True; o.hide_viewport=True
for o in wall_objs:
    o.scale = (SX, SY, 1.0)   # scale footprint X,Y only; height Z unchanged

bpy.context.view_layer.update()

def bounds(objs):
    allc=[(o.matrix_world@mathutils.Vector(c)) for o in objs for c in o.bound_box]
    mn=[min(v[i] for v in allc) for i in range(3)]
    mx=[max(v[i] for v in allc) for i in range(3)]
    return mn,mx

mn,mx = bounds(wall_objs)
ext=[mx[i]-mn[i] for i in range(3)]
cx,cy,cz=[(mn[i]+mx[i])/2 for i in range(3)]
print(f"WALLS n={len(wall_objs)} DOORS(hidden) n={len(door_objs)}")
print(f"bounds min={[round(v) for v in mn]} max={[round(v) for v in mx]}")
print(f"extent mm={[round(v) for v in ext]} = X {ext[0]/1000:.1f}m Y {ext[1]/1000:.1f}m H {ext[2]/1000:.1f}m")
print(f"center={[round(v) for v in (cx,cy,cz)]}")

# camera overview (dollhouse)
cam_data=bpy.data.cameras.new("C"); cam_data.lens=24; cam_data.clip_end=200000
cam=bpy.data.objects.new("C",cam_data); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera=cam
cam.location=(cx, cy+ext[1]*0.85, ext[2]*4.0)
tgt=mathutils.Vector((cx,cy,ext[2]*0.2))
cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()

# world + sun
w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
nt=w.node_tree; nt.nodes["Background"].inputs[0].default_value=(0.9,0.92,0.95,1); nt.nodes["Background"].inputs[1].default_value=1.0
sun=bpy.data.lights.new("S",'SUN'); sun.energy=3.5
so=bpy.data.objects.new("S",sun); bpy.context.scene.collection.objects.link(so)
so.rotation_euler=(math.radians(50),math.radians(35),math.radians(15))

sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=32
sc.render.resolution_x=960; sc.render.resolution_y=540; sc.render.image_settings.file_format='PNG'

bpy.context.view_layer.update()
sc.render.filepath=OUT+"/overview_v2.png"
bpy.ops.render.render(write_still=True)
print("DONE overview_v2.png")
