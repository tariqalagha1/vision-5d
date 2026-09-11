import bpy, mathutils, collections
bpy.ops.import_scene.gltf(filepath=r"C:/Users/admin/workspaces/vision-5d/.exports/96d13d7a-172a-45c2-8746-dad1bf5226f8.glb")
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
print("TOTAL", len(meshes))
groups=collections.defaultdict(list)
for o in meshes:
    cs=[o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    c=tuple(sum(v[i] for v in cs)/len(cs) for i in range(3))
    # name prefix
    name=o.name.split('.')[0]
    key=name
    groups[key].append((round(c[0]),round(c[1]),round(c[2])))
for k,v in sorted(groups.items()):
    xs=[t[0] for t in v]; ys=[t[1] for t in v]; zs=[t[2] for t in v]
    print(f"{k:20s} n={len(v):3d}  X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] Z[{min(zs)},{max(zs)}]")
