import bpy, mathutils, math, os, json

GLB = r"C:/Users/admin/workspaces/vision-5d/.exports/2f4475ad-7ab9-4a00-bb8e-79713f7773cb.glb"
OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
FRAMES = os.path.join(OUT, "frames")
os.makedirs(FRAMES, exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

wall_objs=[]; hide=[]
for o in meshes:
    if o.name.split('.')[0]=='wall_solid': wall_objs.append(o)
    else: hide.append(o)
for o in hide: o.hide_render=True; o.hide_viewport=True
bpy.context.view_layer.update()

def bounds(objs):
    allc=[(o.matrix_world@mathutils.Vector(c)) for o in objs for c in o.bound_box]
    return [min(v[i] for v in allc) for i in range(3)],[max(v[i] for v in allc) for i in range(3)]
mn,mx = bounds(wall_objs)
ext=[mx[i]-mn[i] for i in range(3)]
cx,cy,cz=[(mn[i]+mx[i])/2 for i in range(3)]
W,L,H=ext[0],ext[1],ext[2]
print(json.dumps({"walls":len(wall_objs),"extent_mm":[round(v) for v in ext],
    "center":[round(v) for v in (cx,cy,cz)]}))

# --- floor plane (grounds the building visually) ---
bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, 0))
floor = bpy.context.active_object
floor.scale = (W*1.15/2, L*1.15/2, 1.0)
floor.color = (0.86, 0.86, 0.88, 1.0)

# --- wall color (distinct from floor) ---
for o in wall_objs:
    o.color = (0.62, 0.46, 0.33, 1.0)   # warm tan/brown

# --- camera + light ---
cam_data=bpy.data.cameras.new("C"); cam_data.lens=24; cam_data.clip_end=200000
cam=bpy.data.objects.new("C",cam_data); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera=cam

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
sc.render.film_transparent=False

FPS=30
def V(x,y,z): return mathutils.Vector((x,y,z))
shots=[
 ("overview",   V(cx+W*1.1, cy+L*0.95, H*3.6), V(cx-W*1.1, cy+L*0.7, H*3.0), V(cx,cy,H*0.1), V(cx,cy,H*0.1), 40),
 ("entry",      V(cx, cy+L*0.62, H*1.5),      V(cx, cy+L*0.50, H*1.1),       V(cx,cy-L*0.3,H*0.4), V(cx,cy-L*0.2,H*0.4), 40),
 ("circulation",V(cx, cy-L*0.42, H*1.7),      V(cx, cy+L*0.42, H*1.7),       V(cx,cy-L*0.32,H*0.3), V(cx,cy+L*0.32,H*0.3), 60),
 ("major-space",V(cx+W*0.75, cy, H*1.9),      V(cx+W*0.28, cy, H*1.35),      V(cx,cy,H*0.3), V(cx,cy,H*0.3), 40),
 ("spatial",    V(cx+W*1.15, cy+L*0.55, H*2.1), V(cx+W*0.65, cy-L*0.35, H*2.1), V(cx,cy,H*0.2), V(cx,cy,H*0.2), 40),
 ("closing",    V(cx+W*0.45, cy, H*1.4),      V(cx, cy+L*0.9, H*3.8),        V(cx,cy,H*0.2), V(cx,cy,H*0.2), 40),
]
def ease(t): return t*t*(3-2*t)
total=0; manifest=[]
for si,(name,cs_,ce_,ts_,te_,nf) in enumerate(shots):
    for f in range(nf):
        t=f/(nf-1) if nf>1 else 0; e=ease(t)
        cam.location = cs_.lerp(ce_, e)
        tgt = ts_.lerp(te_, e)
        cam.rotation_euler = (tgt-cam.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        sc.render.filepath = f"{FRAMES}/s{si:02d}_{name}_{f:03d}.png"
        bpy.ops.render.render(write_still=True)
        total+=1
    manifest.append({"shot":name,"frames":nf,"fps":FPS,"duration_s":round(nf/FPS,2)})
    print(f"SHOT DONE {name} ({nf})", flush=True)
json.dump({"manifest":manifest,"total_frames":total,"fps":FPS,
           "extent_mm":[round(v) for v in ext],"walls":len(wall_objs)},
          open(os.path.join(OUT,"shot_manifest.json"),"w"), indent=2)
print(f"ALL RENDERED total_frames={total}")
