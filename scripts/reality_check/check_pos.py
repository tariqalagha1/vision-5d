"""Debug: for a camera position, ray-cast 8 directions + forward aim, report distances."""
import bpy, json, os, math
from mathutils import Vector

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
WALL_H, WALL_T = 2.7, 0.2
gm = json.load(open(os.path.join(BASE, "geometry", "HermesGeometryModel.v5d.json")))
walls = gm["walls"]
minx = min(min(w["x1"], w["x2"]) for w in walls)
miny = min(min(w["y1"], w["y2"]) for w in walls)
lx = lambda x: x - minx
ly = lambda y: y - miny

bpy.ops.wm.read_factory_settings(use_empty=True)
def wmat(n, c):
    m = bpy.data.materials.new(n); m.use_nodes = True
    m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*c, 1.0)
    return m
wall_mat = wmat("M_Wall", (0.90, 0.88, 0.83))
def add_box(cx, cy, cz, sx, sy, sz, rz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    o = bpy.context.object; o.data.materials.append(mat)
    o.scale = (sx, sy, sz); o.rotation_euler = (0,0,rz); o.location = (cx,cy,cz)
for w in walls:
    x1,y1,x2,y2 = lx(w["x1"]), ly(w["y1"]), lx(w["x2"]), ly(w["y2"])
    ln = math.hypot(x2-x1, y2-y1)
    if ln < 1e-6: continue
    add_box((x1+x2)/2, (y1+y2)/2, WALL_H/2, ln, WALL_T, WALL_H, math.atan2(y2-y1, x2-x1), wall_mat)

sc = bpy.context.scene
dg = bpy.context.view_layer.depsgraph

def dist(o, d, maxd=40):
    r = sc.ray_cast(dg, o, d, distance=maxd)
    if not r[0]: return -1
    return (r[1] - o).length

for wx, wy in [(30.5, 23.5), (28.5, 27.5), (36.5, 6.5)]:
    o = Vector((lx(wx), ly(wy), 1.6))
    print(f"pos world=({wx},{wy}) local=({lx(wx):.2f},{ly(wy):.2f})")
    for name, dx, dy in [('N',0,1),('S',0,-1),('E',1,0),('W',-1,0),('NE',.707,.707),('NW',-.707,.707),('SE',.707,-.707),('SW',-.707,-.707)]:
        print(f"  {name}: {dist(o, Vector((dx,dy,0))):.2f}m")
    # down (am I inside a wall?)
    ddown = dist(o, Vector((0,0,-1)), 1.7)
    print(f"  DOWN: {ddown:.2f}m (floor should be ~1.6)")
