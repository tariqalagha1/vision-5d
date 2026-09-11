"""Dump mesh names + world bounds for the multi-room GLB via Blender import."""
import bpy, sys

GLB = r"C:\Users\admin\workspaces\vision-5d\output\RE-SingDetch-FH_AS\exports\RE-SingDetch-FH_AS.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.gltf(filepath=GLB)
except Exception as e:
    print("IMPORT ERROR:", e)

obs = [o for o in bpy.data.objects if o.type == "MESH"]
print(f"TOTAL MESH OBJECTS: {len(obs)}")
print(f"{'name':22s} {'verts':>6s}  X[min,max]  Y[min,max]  Z[min,max]")
for o in sorted(obs, key=lambda x: x.name):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    if not pts:
        print(f"{o.name:22s} EMPTY")
        continue
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx = sum(xs)/len(xs); cy = sum(ys)/len(ys); cz = sum(zs)/len(zs)
    print(f"{o.name:22s} {len(pts):6d}  X[{min(xs):.2f},{max(xs):.2f}] Y[{min(ys):.2f},{max(ys):.2f}] Z[{min(zs):.2f},{max(zs):.2f}]  c=({cx:.2f},{cy:.2f},{cz:.2f})")

# overall scene bounds
allx = [p.x for o in obs for p in (o.matrix_world @ v.co for v in o.data.vertices)]
ally = [p.y for o in obs for p in (o.matrix_world @ v.co for v in o.data.vertices)]
allz = [p.z for o in obs for p in (o.matrix_world @ v.co for v in o.data.vertices)]
print(f"\nSCENE BOUNDS: X[{min(allx):.2f},{max(allx):.2f}] Y[{min(ally):.2f},{max(ally):.2f}] Z[{min(allz):.2f},{max(allz):.2f}]")
