"""PR007R v3 — final: verified cameras for bedroom/kitchen + fast interior dolly."""
import bpy, os
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property_pr007.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-007R"
IMG = os.path.join(OUT, "images")
FRAMES = os.path.join(OUT, "video_frames")
os.makedirs(IMG, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)
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

def shoot(name, pos, tgt, lens=40):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    sc.render.filepath = os.path.join(IMG, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print("RENDERED", name)

# bedroom: west of furniture, aimed at wardrobe (tall, at ~5.5,37)
shoot("master_bedroom", (2.5, 34.5, 3.0), (5.0, 37.5, 1.2))
# kitchen: north of furniture, verified clear LOS to (10.2,35.5)
shoot("kitchen_dining", (10.0, 38.5, 3.0), (10.2, 35.5, 1.0))

# interior dolly through kitchen: north->south along clear corridor
bpy.ops.object.camera_add(location=(10.0, 38.5, 3.0))
cam = bpy.context.object
cam.data.lens = 40
sc.camera = cam
sc.cycles.samples = 8
N = 72  # 3s
for f in range(1, N + 1):
    t = (f - 1) / (N - 1)
    cam.location = Vector((10.0, 38.5 - t * 5.0, 3.0))
    aim(cam, (10.2, 35.5, 1.0))
    sc.frame_set(f)
    sc.render.filepath = os.path.join(FRAMES, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 18 == 0:
        print(f"motion {f}/{N}")

print("PR007R V3 DONE")
