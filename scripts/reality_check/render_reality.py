"""Vision 5D physical reality check — Blender CYCLES CPU render of the real
CAD-derived geometry (walls + floor). Stills + motion frames.

Usage:
  blender --background --python render_reality.py -- stills
  blender --background --python render_reality.py -- motion
"""
import bpy, json, os, math, sys
from mathutils import Vector, Matrix

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
OUT  = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-REALITY-CHECK"
os.makedirs(OUT, exist_ok=True)
FRAMES = os.path.join(OUT, "motion_frames")
os.makedirs(FRAMES, exist_ok=True)

mode = "stills"
if "--" in sys.argv:
    mode = sys.argv[sys.argv.index("--") + 1]

WALL_H, WALL_T = 2.7, 0.2

gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
walls = gm["walls"]
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)
maxx = max(max(w["x1"], w["x2"]) for w in walls) - minx
maxy = max(max(w["y1"], w["y2"]) for w in walls) - miny

def lx(x): return x - minx
def ly(y): return y - miny

bpy.ops.wm.read_factory_settings(use_empty=True)

def wmat(name, color, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m

wall_mat  = wmat("M_Wall",  (0.90, 0.88, 0.83))
floor_mat = wmat("M_Floor", (0.55, 0.47, 0.36))

def add_box(cx, cy, cz, sx, sy, sz, rz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.data.materials.append(mat)
    o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, rz)
    o.location = (cx, cy, cz)

# walls
built = 0
for w in walls:
    x1, y1 = lx(w["x1"]), ly(w["y1"])
    x2, y2 = lx(w["x2"]), ly(w["y2"])
    ln = math.hypot(x2 - x1, y2 - y1)
    if ln < 1e-6:
        continue
    add_box((x1 + x2) / 2, (y1 + y2) / 2, WALL_H / 2, ln, WALL_T, WALL_H,
            math.atan2(y2 - y1, x2 - x1), wall_mat)
    built += 1
print(f"WALLS BUILT: {built}")

# floor slab
bpy.ops.mesh.primitive_cube_add(size=1, location=(maxx / 2, maxy / 2, -0.05))
flr = bpy.context.object
flr.scale = (maxx, maxy, 0.1)
flr.data.materials.append(floor_mat)

sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.78, 0.81, 0.88, 1.0)
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])

bpy.ops.object.light_add(type="SUN", location=(maxx / 2, maxy / 2, 30))
bpy.context.object.data.energy = 3.5
bpy.context.object.rotation_euler = (math.radians(45), 0, math.radians(35))

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.fps = 24
sc.render.image_settings.file_format = "PNG"

def aim(cam, t):
    """Robust look-at: never degenerates regardless of direction (incl. +/-Y)."""
    d = (Vector(t) - cam.location).normalized()
    up = Vector((0, 0, 1))  # world Z is vertical
    if abs(d.dot(up)) > 0.999:
        up = Vector((0, 1, 0))
    right = d.cross(up).normalized()
    real_up = right.cross(d).normalized()
    # camera basis: local X=right, Y=real_up, Z=-d
    mat = Matrix((right, real_up, -d)).transposed()
    cam.rotation_euler = mat.to_euler()

def make_cam(loc, target, lens=36):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = lens
    aim(cam, target)
    sc.camera = cam
    return cam

# The one confirmed enclosed room (8-direction wall test) is around
# world x 28..33, y 20..29. Aim all cameras DIAGONALLY (never along +/-Y)
# because to_track_quat('-Z','Y') degenerates when looking along the up axis.
if mode == "stills":
    sc.cycles.samples = 8
    # OVERVIEW — elevated aerial of whole footprint
    make_cam((maxx / 2, maxy / 2, 62), (maxx / 2, maxy / 2, 0), lens=24)
    sc.render.filepath = os.path.join(OUT, "overview.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED overview.png")

    # INTERIOR 1 — verified 6m room (world 28.5,27.5), looking at NW corner
    make_cam((lx(28.5), ly(27.5), 1.6), (lx(26.5), ly(29.5), 1.5), lens=35)
    sc.render.filepath = os.path.join(OUT, "interior_1.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED interior_1.png")

    # INTERIOR 2 — (world 30.5,23.5) looking N/NE toward the lit wall (distinct view)
    make_cam((lx(30.5), ly(23.5), 1.6), (lx(31.5), ly(26.5), 1.5), lens=35)
    sc.render.filepath = os.path.join(OUT, "interior_2.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED interior_2.png")
    print("STILLS DONE")

elif mode == "motion":
    sc.cycles.samples = 4
    # first-person walk N through the (30.5,23.5) room, looking N (toward light)
    cam = make_cam((lx(30.5), ly(22.5), 1.6), (lx(30.5), ly(26.5), 1.5), lens=35)
    N = 120  # 5s @ 24fps
    y0, y1 = ly(22.5), ly(24.5)
    for f in range(1, N + 1):
        t = (f - 1) / (N - 1)
        cam.location.y = y0 + (y1 - y0) * t
        aim(cam, (lx(30.5), ly(26.5), 1.5))
        sc.frame_set(f)
        sc.render.filepath = os.path.join(FRAMES, f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 24 == 0:
            print(f"motion {f}/{N}")
    print("MOTION DONE")
