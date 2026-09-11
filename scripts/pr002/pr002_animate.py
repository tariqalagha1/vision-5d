"""PR002 Phase 3-5 — Camera plan + animation + render (explicit camera aim).

Modes (from sys.argv after --): 'keys' renders 3 keyframes, 'full' renders all frames.
"""
import bpy, os, json, math, sys, traceback
from mathutils import Vector

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"

FPS = 24
DURATION_S = 5.0
FRAME_END = int(FPS * DURATION_S)  # 120
RES_X, RES_Y = 1280, 720
SAMPLES = 4

MODE = "keys"
if "--" in sys.argv:
    MODE = sys.argv[sys.argv.index("--") + 1]

os.makedirs(OUT_DIR, exist_ok=True)
result = {"success": False, "mode": MODE}

def aim(cam, target):
    direction = (Vector(target) - cam.location).normalized()
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    xs, ys, zs = [], [], []
    for o in obs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    bounds = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]}
    result["bounds"] = {k: [round(v, 3) for v in vv] for k, vv in bounds.items()}

    # Neutral material
    mat = bpy.data.materials.new("PR002_Neutral")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], mat.node_tree.nodes["Material Output"].inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.85, 0.83, 0.78, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    for o in obs:
        if o.data.materials:
            o.data.materials.clear()
        o.data.materials.append(mat)

    # World lighting
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.6, 0.7, 0.9, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # Sun
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 12))
    sun = bpy.context.object
    sun.data.energy = 5.0
    sun.data.angle = 0.2

    # Area fill (above room, gives soft ambient)
    bpy.ops.object.light_add(type="AREA", location=(2.5, -2, 6))
    area = bpy.context.object
    area.data.energy = 250.0
    area.data.size = 9.0

    # ---- Camera plan ----
    target = (2.5, -2.5, 0.8)         # fixed look-at (furniture area)
    pos_start  = (2.5, -10.0, 6.0)    # SHOT 1: exterior wide from open back
    pos_middle = (9.0, -8.0, 3.5)     # SHOT 2: closer 3/4 orbit
    pos_end    = (2.5, 3.0, 7.5)      # SHOT 3: elevated reveal over front wall

    bpy.ops.object.camera_add(location=pos_start)
    cam = bpy.context.object
    cam.name = "PR002_Camera"
    scene.camera = cam
    cam.data.clip_end = 200.0
    cam.data.clip_start = 0.05

    # Keyframes: location + rotation at each position (explicit aim)
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    mid_frame = int(FRAME_END * 0.5)

    scene.frame_current = 1
    cam.location = pos_start
    aim(cam, target)
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_euler", frame=1)

    scene.frame_current = mid_frame
    cam.location = pos_middle
    aim(cam, target)
    cam.keyframe_insert(data_path="location", frame=mid_frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=mid_frame)

    scene.frame_current = FRAME_END
    cam.location = pos_end
    aim(cam, target)
    cam.keyframe_insert(data_path="location", frame=FRAME_END)
    cam.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

    result["camera_plan"] = {
        "fps": FPS, "duration_s": DURATION_S, "frames": FRAME_END,
        "target": list(target),
        "shot1_exterior_frame_1": list(pos_start),
        "shot2_orbit_frame": [mid_frame, list(pos_middle)],
        "shot3_reveal_frame": [FRAME_END, list(pos_end)],
    }

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"

    if MODE == "keys":
        keydir = os.path.join(OUT_DIR, "keyframes")
        os.makedirs(keydir, exist_ok=True)
        keyframes = {"start": 1, "middle": mid_frame, "end": FRAME_END}
        rendered = {}
        for name, frm in keyframes.items():
            scene.frame_current = frm
            outpath = os.path.join(keydir, f"keyframe_{name}_f{frm:04d}.png")
            scene.render.filepath = outpath
            bpy.ops.render.render(write_still=True)
            rendered[name] = outpath
        result["keyframes"] = rendered
    else:
        framedir = os.path.join(OUT_DIR, "frames")
        os.makedirs(framedir, exist_ok=True)
        scene.render.filepath = os.path.join(framedir, "frame_")
        bpy.ops.render.render(animation=True)
        result["frames_dir"] = framedir
        result["frame_count"] = FRAME_END

    result["success"] = True
    print("ANIMATION RENDER OK:", MODE)
    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])
    with open(os.path.join(OUT_DIR, "animate_result.json"), "w") as f:
        json.dump(result, f, indent=2, default=str)
    sys.exit(1)

with open(os.path.join(OUT_DIR, "animate_result.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
