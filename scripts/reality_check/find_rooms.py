"""Build scene, ray-cast 4-direction clearance map, report best interior spots."""
import bpy, json, os, math
from mathutils import Vector

BASE = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS"
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
EYE = 1.6

def hit(origin, direction, maxd=40):
    r = sc.ray_cast(dg, origin, direction, distance=maxd)
    if not r[0]:
        return (False, -1)
    return (True, (r[1] - origin).length)

results = []
for gx in range(28, 66):
    for gy in range(-6, 89):
        o = Vector((lx(gx+0.5), ly(gy+0.5), EYE))
        ds = {}
        for k,(dx,dy) in {'N':(0,1),'S':(0,-1),'E':(1,0),'W':(-1,0)}.items():
            h,d = hit(o, Vector((dx,dy,0)), 40)
            ds[k] = d if h else -1
        if all(v > 0 for v in ds.values()):
            mn = min(ds.values())
            results.append((mn, gx+0.5, gy+0.5, ds))

results.sort(key=lambda r: -r[0])
print(f"ENCLOSED positions (wall in all 4 dirs): {len(results)}")
print("Top 25 by min-clearance:")
for r in results[:25]:
    print(f"  min={r[0]:.2f}m world=({r[1]:.1f},{r[2]:.1f}) N={r[3]['N']:.2f} S={r[3]['S']:.2f} E={r[3]['E']:.2f} W={r[3]['W']:.2f}")
# histogram of min-clearance
buckets = {}
for r in results:
    b = int(r[0]*2)  # 0.5m buckets
    buckets[b] = buckets.get(b,0)+1
print("min-clearance distribution (0.5m buckets):")
for b in sorted(buckets):
    print(f"  {b*0.5:.1f}-{b*0.5+0.5:.1f}m: {buckets[b]}")
