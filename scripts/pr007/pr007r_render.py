"""PR007R — render real physical PNGs + interior motion MP4 from the reconstructed scene."""
import bpy, os
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property_pr007.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-007R"
IMG = os.path.join(OUT, "images")
VID = os.path.join(OUT, "video")
FRAMES = os.path.join(OUT, "video_frames")
os.makedirs(IMG, exist_ok=True)
os.makedirs(VID, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
obs = [o for o in bpy.data.objects if o.type == "MESH"]
print("IMPORTED", len(obs), "objects")

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

def make_cam(pos, tgt, lens):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.data.lens = lens
    sc.camera = cam
    aim(cam, tgt)
    return cam

# 1. overview (high angle)
cam = make_cam((20.0, 30.0, 25.0), (7.0, 35.0, 1.0), 40)
sc.render.filepath = os.path.join(IMG, "property_overview.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(cam, do_unlink=True)
print("RENDERED overview")

# 2. living room (elevated 3/4 view into living furniture cluster at (4.1,36.1))
cam = make_cam((3.0, 31.0, 3.5), (4.2, 36.2, 1.0), 35)
sc.render.filepath = os.path.join(IMG, "living_room.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(cam, do_unlink=True)
print("RENDERED living_room")

# 3. master bedroom (elevated, into bedroom furniture at (4.0,37.6))
cam = make_cam((3.0, 40.5, 3.5), (4.2, 37.4, 1.0), 35)
sc.render.filepath = os.path.join(IMG, "master_bedroom.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(cam, do_unlink=True)
print("RENDERED master_bedroom")

# 4. kitchen/dining (eye-level through clear LOS)
cam = make_cam((10.3, 30.0, 1.6), (10.3, 36.0, 1.0), 40)
sc.render.filepath = os.path.join(IMG, "kitchen_dining.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(cam, do_unlink=True)
print("RENDERED kitchen_dining")

# 5. interior motion: dolly through kitchen/dining area (clear path)
cam = make_cam((10.3, 29.5, 1.7), (10.3, 36.0, 1.0), 40)
N = 96  # 4s @ 24fps
for f in range(1, N + 1):
    t = (f - 1) / (N - 1)
    cam.location = Vector((10.3, 29.5 + t * 4.0, 1.7))
    aim(cam, (10.3, 36.0, 1.0))
    sc.frame_set(f)
    sc.render.filepath = os.path.join(FRAMES, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 24 == 0:
        print(f"motion {f}/{N}")

print("PR007R RENDER DONE")
