"""PR006 stage 5 — simple orbit motion-preview MP4 from the reopened GLB."""
import bpy, os, math
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006\scene\reconstructed_multiroom_property.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-006"
FRAMES_DIR = os.path.join(OUT, "video_frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

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
bpy.ops.object.light_add(type="SUN", location=(40, 40, 30))
bpy.context.object.data.energy = 4.0

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 8
sc.cycles.use_denoising = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.fps = 24

# orbit around the main house (x~[26,40] -> normalized x[0,14], y~[9,33] -> y[0.7,24.7])
C = Vector((7.0, 12.0, 1.0))   # house center (normalized)
R = 28.0                        # orbit radius
Z = 14.0                        # camera height

bpy.ops.object.camera_add(location=(C.x + R, C.y, Z))
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 40
cam.rotation_mode = "QUATERNION"

N = 144  # 6 seconds @ 24fps
for f in range(1, N + 1):
    ang = (f - 1) / N * 2 * math.pi
    cam.location = Vector((C.x + R * math.cos(ang), C.y + R * math.sin(ang), Z))
    d = (C - cam.location).normalized()
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    sc.frame_set(f)
    sc.render.filepath = os.path.join(FRAMES_DIR, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 24 == 0:
        print(f"rendered {f}/{N}")

print("ORBIT FRAMES DONE")
