"""PR007 — re-render living + bedroom interiors with elevated cameras."""
import bpy, os
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property_pr007.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\images"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1.0)
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(20, 35, 20))
bpy.context.object.data.energy = 4.0

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720

def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=35):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

# elevated interior views (above 2.7m walls, looking down into rooms)
shoot("living_room_repaired", (2.5, 30.5, 4.0), (4.5, 36.0, 0.3))
shoot("master_bedroom_repaired", (2.5, 41.5, 4.0), (4.5, 37.0, 0.3))

print("DONE")
