"""PR006 stage 3/4 — reopen the exported GLB from disk and render corrected images.

Proves the GLB is openable (re-imports it) and renders all 7 views with cameras
placed in verified-open floor positions.
"""
import bpy, os, math
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\images"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
obs = [o for o in bpy.data.objects if o.type == "MESH"]
print("IMPORTED", len(obs), "mesh objects from GLB")

# world + sun
sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1.0)
bg.inputs["Strength"].default_value = 1.0
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(40, 40, 25))
bpy.context.object.data.energy = 4.0

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720

# scene bounds
allx = [p.x for o in obs for p in (o.matrix_world @ v.co for v in o.data.vertices)]
ally = [p.y for o in obs for p in (o.matrix_world @ v.co for v in o.data.vertices)]
maxx, maxy = max(allx), max(ally)
cx, cy = maxx / 2, maxy / 2
print(f"scene bounds: x[0,{maxx:.1f}] y[0,{maxy:.1f}]")

def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=50):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

shoot("overview", (cx + maxx * 0.9, cy - maxy * 0.7, maxx * 0.7), (cx, cy, 1.0))
shoot("top_view", (cx, cy, max(maxx, maxy) * 1.2), (cx, cy, 0))
shoot("living_room", (28.0, 13.0, 1.6), (28.0, 20.0, 1.2))
shoot("kitchen_dining", (34.0, 13.0, 1.6), (34.0, 20.0, 1.2))
shoot("master_bedroom", (30.0, 24.0, 1.6), (30.0, 17.0, 1.2))
shoot("hallway", (30.0, 12.0, 1.6), (30.0, 22.0, 1.2))
shoot("bathroom", (32.0, 24.0, 1.6), (32.0, 17.0, 1.2))

print("PR006 RE-RENDER DONE")
