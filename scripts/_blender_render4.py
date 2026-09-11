import bpy, sys, json
from mathutils import Vector

glb = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

# Inspect scene structure
print("SCENE objects:", len(bpy.context.scene.objects))
print("SCENE collection:", bpy.context.scene.collection.name, "children:", [c.name for c in bpy.context.scene.collection.children])
print("view_layer objects:", len(list(bpy.context.view_layer.objects)))
print("master collection objects:", len(list(bpy.context.scene.collection.objects)))

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
allx=[]; ally=[]; allz=[]
for o in objs:
    for v in o.data.vertices:
        w = o.matrix_world @ Vector(v.co)
        allx.append(w.x); ally.append(w.y); allz.append(w.z)
cx=(min(allx)+max(allx))/2; cy=(min(ally)+max(ally))/2; cz=(min(allz)+max(allz))/2
span=max(max(allx)-min(allx), max(ally)-min(ally), max(allz)-min(allz)) or 1

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 50
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = Vector((cx+span*0.9, cy+span*1.2, cz+span*0.9))
dirn = Vector((cx,cy,cz)) - cam.location
cam.rotation_euler = dirn.to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("W"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.5,0.5,0.55,1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

sun_data = bpy.data.lights.new("Sun", type="SUN"); sun_data.energy = 3.0
sun = bpy.data.objects.new("Sun", sun_data)
bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (0.7, 0.3, 0.4)

mat = bpy.data.materials.new("M"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.85,0.7,0.5,1)
for o in objs:
    o.data.materials.clear()
    o.data.materials.append(mat)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "CPU"
bpy.context.scene.cycles.samples = 48
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDER_DONE " + out)
