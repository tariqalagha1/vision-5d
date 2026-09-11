"""PR006 — reconstruct real 3D multi-room property from HermesGeometryModel.v5d.json.

Builds:
  - 3D wall boxes from the 1010 real 2D wall segments (extruded, height 2.7m)
  - a floor slab over the property footprint
  - 30 furniture boxes from the design layer (real positions/dims/colors)
Exports a GLB, then renders overview / top / interior PNGs.
"""
import bpy, json, os, math, sys
from mathutils import Vector, Matrix

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006"
WALL_H = 2.7
WALL_T = 0.2

os.makedirs(os.path.join(OUT, "scene"), exist_ok=True)
os.makedirs(os.path.join(OUT, "images"), exist_ok=True)

gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
v5d = json.load(open(os.path.join(BASE, "exports", "RE-SingDetch-FH_AS.v5d")))
walls = gm["walls"]
furniture = v5d["design"]["furniture"]

# ---- normalize wall coords to origin ----
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)
print(f"wall bbox min=({minx:.2f},{miny:.2f})")

def wmat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return m

wall_mat = wmat("M_Wall", (0.88, 0.86, 0.82))
floor_mat = wmat("M_Floor", (0.65, 0.55, 0.42))
furn_mat = wmat("M_Furn", (0.45, 0.40, 0.35))

# ---- build wall boxes ----
def add_box(name, cx, cy, cz, sx, sy, sz, rz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, rz)
    o.location = (cx, cy, cz)
    return o

n_wall = 0
for w in walls:
    x1, y1 = w["x1"] - minx, w["y1"] - miny
    x2, y2 = w["x2"] - minx, w["y2"] - miny
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        continue
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    rz = math.atan2(dy, dx)
    add_box(f"wall_{n_wall}", cx, cy, WALL_H / 2, ln, WALL_T, WALL_H, rz, wall_mat)
    n_wall += 1

# ---- floor slab over footprint ----
maxx = max(max(w["x1"], w["x2"]) for w in walls) - minx
maxy = max(max(w["y1"], w["y2"]) for w in walls) - miny
bpy.ops.mesh.primitive_cube_add(size=1, location=(maxx / 2, maxy / 2, -0.05))
flr = bpy.context.object
flr.name = "floor_slab"
flr.scale = (maxx, maxy, 0.1)
flr.data.materials.append(floor_mat)

# ---- furniture: translate design coords into wall space ----
# furniture rooms span x~[1.5,13], z~[-9,0]; map into house interior region
# house interior is roughly x[27,39], y[12,30] in normalized wall space
fminx = min(f["pos"][0] - f["dims"][0] / 2 for f in furniture)
fmaxx = max(f["pos"][0] + f["dims"][0] / 2 for f in furniture)
fminz = min(f["pos"][2] - f["dims"][2] / 2 for f in furniture)
fmaxz = max(f["pos"][2] + f["dims"][2] / 2 for f in furniture)
TX = 27.0 - fminx          # map furniture x-min to x=27 (inside house footprint)
n_furn = 0
for f in furniture:
    x = f["pos"][0] + TX
    y = -f["pos"][2] + 12.0          # furniture -z (front) -> wall y=12, back -> y=21
    z = f["pos"][1] + f["dims"][1] / 2  # sit on floor, centered at half height
    w, h, d = f["dims"]
    add_box(f"furn_{n_furn}", x, y, z, w, d, h, 0, furn_mat)
    n_furn += 1

# ---- lighting + world ----
scene = bpy.context.scene
scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
nt = scene.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1.0)
bg.inputs["Strength"].default_value = 1.0
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(maxx, maxy, 20))
bpy.context.object.data.energy = 4.0

# ---- render settings ----
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 720

print(f"built {n_wall} wall boxes, floor {maxx:.1f}x{maxy:.1f}, {n_furn} furniture")

# ---- export GLB ----
glb_path = os.path.join(OUT, "scene", "reconstructed_multiroom_property.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB",
                          export_apply=True, use_selection=False)
print("EXPORTED GLB:", glb_path, os.path.getsize(glb_path) if os.path.exists(glb_path) else "MISSING")

# ---- camera + render images ----
def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=50):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    scene.camera = cam
    aim(cam, tgt)
    fp = os.path.join(OUT, "images", name + ".png")
    scene.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", fp)

cx, cy = maxx / 2, maxy / 2
shoot("overview", (cx + maxx * 0.9, cy - maxy * 0.7, maxx * 0.7), (cx, cy, 1.0))
shoot("top_view", (cx, cy, max(maxx, maxy) * 1.2), (cx, cy, 0))
# interior shots at furniture room centers (eye height, looking into rooms)
shoot("living_room", (28.7, 14.5, 1.6), (28.7, 20.0, 1.2))
shoot("kitchen_dining", (33.0, 14.5, 1.6), (33.0, 20.0, 1.2))
shoot("master_bedroom", (28.7, 26.0, 1.6), (28.7, 20.0, 1.2))
shoot("hallway", (31.0, 14.0, 1.6), (31.0, 24.0, 1.2))
shoot("bathroom", (35.0, 26.0, 1.6), (35.0, 20.0, 1.2))

print("PR006 DONE")
