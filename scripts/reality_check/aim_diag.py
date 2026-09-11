import bpy, math
from mathutils import Vector, Matrix

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def aim_manual(cam, t):
    d = (Vector(t) - cam.location).normalized()
    up = Vector((0, 0, 1))
    if abs(d.dot(up)) > 0.999:
        up = Vector((0, 1, 0))
    right = d.cross(up).normalized()
    real_up = right.cross(d).normalized()
    mat = Matrix((right, real_up, -d)).transposed()
    cam.rotation_euler = mat.to_euler()

def aim_track(cam, t):
    d = (Vector(t) - cam.location).normalized()
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def report(cam, label):
    bpy.context.view_layer.update()
    m = cam.matrix_world
    fwd = -m.col[2].xyz  # camera forward = -Z local
    up  = m.col[1].xyz   # camera up = +Y local
    right = m.col[0].xyz
    print(f"{label}: fwd={tuple(round(x,3) for x in fwd)} up={tuple(round(x,3) for x in up)} right={tuple(round(x,3) for x in right)}")

# test 1: diagonal NE (like interior_1)
for name, fn in [("manual", aim_manual), ("track", aim_track)]:
    bpy.ops.object.camera_add(location=(3.72, 31.26, 1.6))
    cam = bpy.context.object
    fn(cam, (6.22, 36.26, 1.5))
    report(cam, name + " NE")

# test 2: looking north (+Y)
for name, fn in [("manual", aim_manual), ("track", aim_track)]:
    bpy.ops.object.camera_add(location=(30.8, 23.5, 1.6))
    cam = bpy.context.object
    fn(cam, (30.8, 30.0, 1.5))
    report(cam, name + " North")
