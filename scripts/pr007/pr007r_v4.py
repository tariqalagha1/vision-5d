"""PR007R v4 — FINAL: rebuild scene with high-contrast furniture + render all outputs."""
import bpy, json, os, math
from mathutils import Vector

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-007R"
IMG = os.path.join(OUT, "images")
VID = os.path.join(OUT, "video")
FRAMES = os.path.join(OUT, "video_frames")
for d in (IMG, VID, FRAMES):
    os.makedirs(d, exist_ok=True)
for f in os.listdir(FRAMES):
    os.remove(os.path.join(FRAMES, f))

WALL_H, WALL_T = 2.7, 0.2
S, TX, TY = 1.0, 0.0, 31.0

gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
v5d = json.load(open(os.path.join(BASE, "exports", "RE-SingDetch-FH_AS.v5d")))
walls = gm["walls"]
furn = v5d["design"]["furniture"]
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)

bpy.ops.wm.read_factory_settings(use_empty=True)

def wmat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return m

wall_mat = wmat("M_Wall", (0.90, 0.88, 0.84))
floor_mat = wmat("M_Floor", (0.62, 0.54, 0.42))
furn_mat = wmat("M_Furn", (0.52, 0.30, 0.14))  # rich wood brown (high contrast)

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
    add_box((x1 + x2) / 2, (y1 + y2) / 2, WALL_H / 2, ln, WALL_T, WALL_H,
            math.atan2(y2 - y1, x2 - x1), wall_mat)

maxx = max(max(w["x1"], w["x2"]) for w in walls) - minx
maxy = max(max(w["y1"], w["y2"]) for w in walls) - miny
bpy.ops.mesh.primitive_cube_add(size=1, location=(maxx / 2, maxy / 2, -0.05))
flr = bpy.context.object
flr.scale = (maxx, maxy, 0.1)
flr.data.materials.append(floor_mat)

for f in furn:
    wx = TX + S * f["pos"][0]
    wy = TY + S * (-f["pos"][2])
    wz = f["pos"][1] + f["dims"][1] / 2
    w, h, d = f["dims"]
    add_box(wx, wy, wz, S * w, S * d, S * h, 0, furn_mat)

sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.75, 0.78, 0.85, 1.0)
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(maxx, maxy, 25))
bpy.context.object.data.energy = 4.5

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.fps = 24

def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=40):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(IMG, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

shoot("property_overview", (20.0, 30.0, 25.0), (7.0, 35.0, 1.0))
shoot("living_room", (3.0, 31.0, 3.5), (4.2, 36.2, 1.0))       # PROVEN geometry
shoot("master_bedroom", (2.9, 32.5, 3.5), (4.1, 37.7, 1.0))    # analogous to living
shoot("kitchen_dining", (9.1, 30.4, 3.5), (10.3, 35.6, 1.0))   # analogous to living

# interior motion: lateral dolly across the living furniture (proven-readable region)
bpy.ops.object.camera_add(location=(2.5, 31.0, 3.5))
cam = bpy.context.object
cam.data.lens = 40
sc.camera = cam
sc.cycles.samples = 8
N = 72  # 3s
for f in range(1, N + 1):
    t = (f - 1) / (N - 1)
    cam.location = Vector((2.5 + t * 3.0, 31.0, 3.5))
    aim(cam, (4.2, 36.2, 1.0))
    sc.frame_set(f)
    sc.render.filepath = os.path.join(FRAMES, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 18 == 0:
        print(f"motion {f}/{N}")

# export rebuilt GLB (with high-contrast furniture) too
glb_path = os.path.join(OUT, "scene", "reconstructed_multiroom_property_007r.glb")
os.makedirs(os.path.dirname(glb_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", export_apply=True, use_selection=False)
print("EXPORTED", glb_path, os.path.getsize(glb_path))

print("PR007R V4 DONE")
