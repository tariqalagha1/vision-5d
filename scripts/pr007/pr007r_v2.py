"""PR007R v2 — elevated cameras (reliable) for bedroom/kitchen + elevated orbit motion."""
import bpy, os, math
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property_pr007.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-007R"
IMG = os.path.join(OUT, "images")
FRAMES = os.path.join(OUT, "video_frames")
os.makedirs(IMG, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)
# clear old motion frames
for f in os.listdir(FRAMES):
    os.remove(os.path.join(FRAMES, f))

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
bpy.ops.object.light_add(type="SUN", location=(20, 35, 25))
bpy.context.object.data.energy = 4.0

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.fps = 24

def aim(c, t):
    d = (Vector(t) - c.location).normalized()
    c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def shoot(name, pos, tgt, lens=35):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(IMG, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

# bedroom (elevated, into bedroom furniture at (4.0,37.6))
shoot("master_bedroom", (3.0, 31.5, 3.5), (4.2, 37.4, 1.0))
# kitchen/dining (elevated, into kitchen furniture at (10.2,35.5))
shoot("kitchen_dining", (10.0, 31.0, 3.5), (10.3, 35.5, 1.0))

# elevated orbit motion around the living furniture cluster (reliable, above walls)
C = Vector((4.0, 36.0, 1.0))
bpy.ops.object.camera_add(location=(C.x + 3.5, C.y, 3.5))
cam = bpy.context.object
cam.data.lens = 35
sc.camera = cam
N = 96  # 4s
for f in range(1, N + 1):
    ang = (f - 1) / N * math.pi * 0.8 + math.pi * 0.6   # partial orbit
    cam.location = Vector((C.x + 3.5 * math.cos(ang), C.y + 3.5 * math.sin(ang), 3.5))
    aim(cam, (C.x, C.y, 0.8))
    sc.frame_set(f)
    sc.render.filepath = os.path.join(FRAMES, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 24 == 0:
        print(f"motion {f}/{N}")

print("PR007R V2 DONE")
