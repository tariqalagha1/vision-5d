"""PR006 — re-render the 2 weak interior views with furniture-facing cameras."""
import bpy, os
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property.glb"
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
bpy.ops.object.light_add(type="SUN", location=(40, 40, 25))
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

def shoot(name, pos, tgt):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = 35  # wider to see more room
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

# living furniture: sofa(28.5,14.5) tv(28.5,16.5) coffee(31,14.5) plant(28.5,20.5)
shoot("living_room", (29.5, 11.0, 1.6), (29.0, 17.5, 1.0))
# bedroom furniture: bed(28.75,17) wardrobe(31,19) nightstand(31,17)
shoot("master_bedroom", (29.5, 13.0, 1.6), (29.5, 19.5, 1.0))

print("DONE")
