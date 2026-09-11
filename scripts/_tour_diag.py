import bpy, mathutils, math
bpy.ops.import_scene.gltf(filepath=r"C:/Users/admin/workspaces/vision-5d/.exports/96d13d7a-172a-45c2-8746-dad1bf5226f8.glb")
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
print("TOTAL", len(meshes))

def c(o):
    xs=[o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    return tuple(sum(v[i] for v in xs)/len(xs) for i in range(3))

centers=[c(o) for o in meshes]
xs=[c[0] for c in centers]; ys=[c[1] for c in centers]; zs=[c[2] for c in centers]
print("center X range", round(min(xs)), round(max(xs)))
print("center Y range", round(min(ys)), round(max(ys)))
print("center Z range", round(min(zs)), round(max(zs)))

def bucket(vals, lo, hi, n=10):
    b=[0]*n; w=(hi-lo)/n
    for v in vals:
        i=int((v-lo)/w); i=max(0,min(n-1,i)); b[i]+=1
    return b
print("X hist", bucket(xs, min(xs), max(xs)))
print("Y hist", bucket(ys, min(ys), max(ys)))
print("Z hist", bucket(zs, min(zs), max(zs)))

# overall world bounds (union of mesh bounds)
mn=[min(vals[i] for vals in [(o.matrix_world@mathutils.Vector(c)) for o in meshes for c in o.bound_box]) for i in range(3)]
# simpler: iterate
allc=[(o.matrix_world@mathutils.Vector(c)) for o in meshes for c in o.bound_box]
mn=[min(v[i] for v in allc) for i in range(3)]
mx=[max(v[i] for v in allc) for i in range(3)]
print("OVERALL min", [round(v) for v in mn], "max", [round(v) for v in mx], "extent", [round(mx[i]-mn[i]) for i in range(3)])
