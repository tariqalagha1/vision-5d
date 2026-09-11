"""Debug: build scene, aim interior camera, print its real orientation, render."""
import bpy, json, os, math
from mathutils import Vector, Matrix

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
OUT  = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-REALITY-CHECK"

WALL_H, WALL_T = 2.7, 0.2
gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
walls = gm["walls"]
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)
maxx = max(max(w["x1"], w["x2"]) for w in walls) - minx
maxy = max(max(w["y1"], w["y2"]) for w in walls) - miny
lx = lambda x: x - minx
ly = lambda y: y - miny

bpy.ops.wm.read_factory_settings(use_empty=True)
def wmat(n, c):
    m = bpy.data.materials.new(n); m.use_nodes = True
    m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*c, 1.0)
    m.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.9
    return m
wall_mat = wmat("M_Wall", (0.90, 0.88, 0.83))
floor_mat = wmat("M_Floor", (0.55, 0.47, 0.36))
def add_box(cx, cy, cz, sx, sy, sz, rz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    o = bpy.context.object; o.data.materials.append(mat)
    o.scale = (sx, sy, sz); o.rotation_euler = (0,0,rz); o.location = (cx,cy,cz)
for w in walls:
    x1,y1,x2,y2 = lx(w["x1"]), ly(w["y1"]), lx(w["x2"]), ly(w["y2"])
    ln = math.hypot(x2-x1, y2-y1)
    if ln < 1e-6: continue
    add_box((x1+x2)/2, (y1+y2)/2, WALL_H/2, ln, WALL_T, WALL_H, math.atan2(y2-y1, x2-x1), wall_mat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(maxx/2, maxy/2, -0.05))
flr = bpy.context.object; flr.scale = (maxx, maxy, 0.1); flr.data.materials.append(floor_mat)

sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Color"].default_value = (0.4, 0.42, 0.5, 1.0)
o = nt.nodes.new("ShaderNodeOutputWorld"); nt.links.new(bg.outputs["Background"], o.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(maxx/2, maxy/2, 30))
bpy.context.object.data.energy = 3.5
bpy.context.object.rotation_euler = (math.radians(45), 0, math.radians(35))
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
sc.cycles.samples = 8
sc.render.resolution_x = 1280; sc.render.resolution_y = 720

def aim(cam, t):
    d = (Vector(t) - cam.location).normalized()
    up = Vector((0,0,1))
    if abs(d.dot(up)) > 0.999: up = Vector((0,1,0))
    right = d.cross(up).normalized()
    real_up = right.cross(d).normalized()
    mat = Matrix((right, real_up, -d)).transposed()
    cam.rotation_euler = mat.to_euler()

bpy.ops.object.camera_add(location=(lx(36.5), ly(6.5), 1.6))
cam = bpy.context.object
cam.data.lens = 35
aim(cam, (lx(34.5), ly(8.5), 1.5))
sc.camera = cam
bpy.context.view_layer.update()
m = cam.matrix_world
fwd = -m.col[2].xyz; up = m.col[1].xyz
print(f"CAMERA: loc={tuple(round(x,2) for x in cam.location)} fwd={tuple(round(x,3) for x in fwd)} up={tuple(round(x,3) for x in up)}")

# ray-cast from camera along fwd to find what it hits (first object)
def raycast(origin, direction, max_dist=100):
    res = sc.ray_cast(bpy.context.view_layer.depsgraph, origin, direction, distance=max_dist)
    return res
hit = raycast(cam.location, fwd)
print(f"RAYCAST along fwd: hit={hit[0]} obj={hit[4].name if hit[0] else None} dist={hit[3]:.2f} pos={tuple(round(x,2) for x in hit[1]) if hit[0] else None}")

sc.render.filepath = os.path.join(OUT, "debug_interior2.png")
bpy.ops.render.render(write_still=True)
print("DEBUG RENDER DONE")
