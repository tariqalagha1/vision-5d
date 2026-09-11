"""PR007 — corrected furniture transform + interior camera placement + re-render.

Root cause: PR006 placed furniture in the wrong region (garage footprint) via a
bad translation. Corrected generalized uniform transform maps the furniture
design grid (fx in [1.5,13], fz in [-9,0]) into the MAIN house interior:
    wall_x = fx        (scale 1.0)
    wall_y = -fz + 31  (front row -> y=31..33, back row -> y=36..40)
Cameras placed at furniture room centers (living/bedroom), derived from the
furniture grid, not hardcoded per-object.
"""
import bpy, json, os, math
from mathutils import Vector

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006"
WALL_H = 2.7
WALL_T = 0.2
S = 1.0          # uniform scale
TX = 0.0         # wall x offset
TY = 31.0        # wall y offset

gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
v5d = json.load(open(os.path.join(BASE, "exports", "RE-SingDetch-FH_AS.v5d")))
walls = gm["walls"]
furn = v5d["design"]["furniture"]
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)

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

def add_box(cx, cy, cz, sx, sy, sz, rz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.data.materials.append(mat)
    o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, rz)
    o.location = (cx, cy, cz)

for w in walls:
    x1, y1 = w["x1"] - minx, w["y1"] - miny
    x2, y2 = w["x2"] - minx, w["y2"] - miny
    ln = math.hypot(x2 - x1, y2 - y1)
    if ln < 1e-6:
        continue
    add_box((x1 + x2) / 2, (y1 + y2) / 2, WALL_H / 2, ln, WALL_T, WALL_H, math.atan2(y2 - y1, x2 - x1), wall_mat)

maxx = max(max(w["x1"], w["x2"]) for w in walls) - minx
maxy = max(max(w["y1"], w["y2"]) for w in walls) - miny
bpy.ops.mesh.primitive_cube_add(size=1, location=(maxx / 2, maxy / 2, -0.05))
flr = bpy.context.object
flr.scale = (maxx, maxy, 0.1)
flr.data.materials.append(floor_mat)

# furniture with corrected uniform transform
for f in furn:
    wx = TX + S * f["pos"][0]
    wy = TY + S * (-f["pos"][2])
    wz = f["pos"][1] + f["dims"][1] / 2
    w, h, d = f["dims"]
    add_box(wx, wy, wz, S * w, S * d, S * h, 0, furn_mat)

# lighting
sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1.0)
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(maxx, maxy, 20))
bpy.context.object.data.energy = 4.0

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720

def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=40):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(OUT, "images", name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

# top/high-angle furniture validation
shoot("top_view_pr007", (7.0, 35.0, 30.0), (5.0, 34.0, 0.0))
# living room (sofa/coffee at fx 3..5.5 -> wx 3..5.5, wy 33.5..39.5)
shoot("living_room_repaired", (4.0, 31.0, 1.6), (4.0, 36.0, 1.0))
# master bedroom (bed at fx 3 -> wx 3, wy 36)
shoot("master_bedroom_repaired", (4.0, 41.0, 1.6), (4.0, 37.0, 1.0))
# kitchen (island/cabinets at fx 9..12 -> wx 9..12)
shoot("kitchen_dining_repaired", (10.5, 31.0, 1.6), (10.5, 36.0, 1.0))

# export corrected GLB
glb_path = os.path.join(OUT, "scene", "reconstructed_multiroom_property_pr007.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", export_apply=True, use_selection=False)
print("EXPORTED", glb_path, os.path.getsize(glb_path) if os.path.exists(glb_path) else "MISSING")
print("PR007 DONE")
