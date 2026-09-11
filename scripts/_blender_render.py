"""Render the GLB to a PNG — robust camera aim via Track-To + bright world."""
import bpy
import sys
import mathutils
from mathutils import Vector

glb = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
xs = []; ys = []; zs = []
for o in objs:
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v)
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
cx = (min(xs)+max(xs))/2; cy = (min(ys)+max(ys))/2; cz = (min(zs)+max(zs))/2
span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)) or 1.0
center = Vector((cx, cy, cz))

# Empty as aim target
empty = bpy.data.objects.new("Aim", None)
bpy.context.scene.collection.objects.link(empty)
empty.location = center

# Camera
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 35
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = center + Vector((span*1.2, span*1.6, span*1.1))
track = cam.constraints.new(type="TRACK_TO")
track.target = empty
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
bpy.context.scene.camera = cam

# Bright world
world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.5, 0.5, 0.55, 1.0)
bg.inputs[1].default_value = 1.5

# Sun light (directional, points at center)
light_data = bpy.data.lights.new("Sun", type="SUN")
light_data.energy = 5.0
light = bpy.data.objects.new("Sun", light_data)
bpy.context.scene.collection.objects.link(light)
light.location = center + Vector((span*0.3, span*1.5, span*0.8))
ltrack = light.constraints.new(type="TRACK_TO")
ltrack.target = empty
ltrack.track_axis = "TRACK_NEGATIVE_Z"
ltrack.up_axis = "UP_Y"

# Force visible materials: assign a bright material to any mesh without one
mat = bpy.data.materials.new("Bright")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0)
for o in objs:
    if not o.data.materials or o.data.materials[0] is None:
        o.data.materials.append(mat)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "CPU"
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)

import json
print("RENDER_RESULT " + json.dumps({"output": out, "objects": len(objs),
      "center": [round(cx,1), round(cy,1), round(cz,1)], "span": round(span,1)}))
