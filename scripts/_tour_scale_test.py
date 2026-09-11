import bpy, sys, math, os

# --- CONFIG ---
GLB = r"C:/Users/admin/workspaces/vision-5d/.exports/96d13d7a-172a-45c2-8746-dad1bf5226f8.glb"
OUT = r"C:/Users/admin/workspaces/vision-5d/evidence/runs/vision5d-customer-tour-001"
os.makedirs(OUT, exist_ok=True)

# scale correction: 1 DXF unit = 1 foot = 304.8 mm (SCALE_MATERIAL_FOR_TOUR fix)
# wall region: X extent 1166mm -> 40.1 units -> 29.08 mm/unit ; Z extent 1955mm -> 80.19 units -> 24.38 mm/unit
SX = 304.8 / 29.08
SZ = 304.8 / 24.38

# --- clean scene ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# --- import GLB ---
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print(f"IMPORTED {len(meshes)} mesh objects")

# --- classify walls vs doors by bounding box ---
import mathutils
def world_bounds(o):
    # object-space corners
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs=[c.x for c in corners]; ys=[c.y for c in corners]; zs=[c.z for c in corners]
    return (min(xs),min(ys),min(zs)), (max(xs),max(ys),max(zs))

wall_objs=[]; door_objs=[]; other=[]
for o in meshes:
    mn,mx = world_bounds(o)
    cx=(mn[0]+mx[0])/2; cz=(mn[2]+mx[2])/2
    # doors cluster near origin (x near 0, z near 0); walls at x~700, z~640
    if abs(cx) < 700 and abs(cz) < 200:
        door_objs.append(o)
    else:
        wall_objs.append(o)

print(f"wall meshes: {len(wall_objs)}, door meshes: {len(door_objs)}")

# --- apply scale correction to walls (non-uniform XZ) ---
for o in wall_objs:
    o.scale = (SX, 1.0, SZ)
    o.matrix_world = mathutils.Matrix.Diagonal((SX,1.0,SZ,1.0)) @ o.matrix_world

# --- hide door meshes (misplaced pre-existing artifact) ---
for o in door_objs:
    o.hide_render = True
    o.hide_viewport = True

bpy.context.view_layer.update()

# --- compute wall bounds after scaling ---
mn,mx = None,None
for o in wall_objs:
    bmn,bmx = world_bounds(o)
    mn = bmn if mn is None else tuple(min(a,b) for a,b in zip(mn,bmn))
    mx = bmx if mx is None else tuple(max(a,b) for a,b in zip(mx,bmx))
ext = tuple(mx[i]-mn[i] for i in range(3))
center = tuple((mn[i]+mx[i])/2 for i in range(3))
print(f"WALL BOUNDS after scale: min={[round(v) for v in mn]} max={[round(v) for v in mx]}")
print(f"EXTENT (mm): {[round(v) for v in ext]} = X {ext[0]/1000:.1f}m, Z {ext[2]/1000:.1f}m, H {ext[1]/1000:.1f}m")
print(f"CENTER: {[round(v) for v in center]}")

# --- camera setup (overview) ---
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 24
cam_data.clip_end = 200000
cam_obj = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# overview camera: high angle, full building in view
cx,cy,cz = center
# distance = 2.6x extent
dist = max(ext[0], ext[2]) * 2.0
cam_obj.location = (cx, ext[1]*2.5, cz + dist*0.9)
dir = mathutils.Vector((cx, ext[1]*0.3, cz)) - cam_obj.location
cam_obj.rotation_euler = dir.to_track_quat('-Z','Y').to_euler()

# --- lighting + world ---
bpy.context.scene.world = bpy.data.worlds.new("W")
bpy.context.scene.world.use_nodes = True
nt = bpy.context.scene.world.node_tree
nt.nodes["Background"].inputs[1].default_value = 1.0
nt.nodes["Background"].inputs[0].default_value = (0.9,0.92,0.95,1)

sun = bpy.data.lights.new("Sun", 'SUN')
sun.energy = 4.0
sun_obj = bpy.data.objects.new("Sun", sun)
bpy.context.scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(45), math.radians(30), math.radians(20))

# --- render settings ---
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'CPU'
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.film_transparent = False

bpy.context.view_layer.update()
bpy.context.scene.render.filepath = OUT + "/test_overview.png"
bpy.ops.render.render(write_still=True)
print("TEST RENDER DONE ->", OUT + "/test_overview.png")
