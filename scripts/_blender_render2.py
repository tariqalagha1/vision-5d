import bpy, sys, json
import mathutils
from mathutils import Vector

glb = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 1 + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
# Print each object location + dimensions
info = []
for o in objs[:6]:
    info.append({"name": o.name, "loc": [round(o.location.x,0), round(o.location.y,0), round(o.location.z,0)],
                 "dim": [round(o.dimensions.x,0), round(o.dimensions.y,0), round(o.dimensions.z,0)]})
print("OBJECT_INFO " + json.dumps(info))

# Dead simple top-down orthographic
xs=[o.location.x for o in objs]; ys=[o.location.y for o in objs]; zs=[o.location.z for o in objs]
# use mesh vertices to get real bounds
allx=[]; ally=[]; allz=[]
for o in objs:
    for v in o.data.vertices:
        w = o.matrix_world @ Vector(v.co)
        allx.append(w.x); ally.append(w.y); allz.append(w.z)
cx=(min(allx)+max(allx))/2; cy=(min(ally)+max(ally))/2; cz=(min(allz)+max(allz))/2
span=max(max(allx)-min(allx), max(ally)-min(ally), max(allz)-min(allz)) or 1
print("TRUE_BOUNDS " + json.dumps({"cx":round(cx,0),"cy":round(cy,0),"cz":round(cz,0),"span":round(span,0),
      "x":[round(min(allx),0),round(max(allx),0)],"y":[round(min(ally),0),round(max(ally),0)],"z":[round(min(allz),0),round(max(allz),0)]}))

# Orthographic top-down camera
cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = span * 1.4
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (cx, cy, cz + span*1.5)
cam.rotation_euler = (0, 0, 0)  # looking -Z (down)
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("W"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.7,0.7,0.7,1)
world.node_tree.nodes["Background"].inputs[1].default_value = 2.0

mat = bpy.data.materials.new("M"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.85,0.85,0.85,1)
for o in objs:
    if not o.data.materials or o.data.materials[0] is None:
        o.data.materials.append(mat)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "CPU"
bpy.context.scene.cycles.samples = 32
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDER_DONE " + out)
