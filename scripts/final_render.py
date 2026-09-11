import bpy, os, json, hashlib, math, time, glob, sys, traceback

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\final_render"
FRAMES = 30
OUT_JSON = os.path.join(OUT_DIR, "render_result.json")

os.makedirs(OUT_DIR, exist_ok=True)
result = {"success": False, "error": "", "traceback": ""}

def write_result():
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    result["objects"] = len(obs)
    result["vertices"] = sum(len(o.data.vertices) for o in obs)

    scene = bpy.context.scene

    # Camera orbit
    bpy.ops.object.camera_add(location=(10, -10, 5))
    cam = bpy.context.object; cam.name = "CinematicCamera"; scene.camera = cam
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(2.5, 2.0, 1.5))
    target = bpy.context.object
    tr = cam.constraints.new(type="TRACK_TO")
    tr.target = target; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"

    scene.frame_start = 1; scene.frame_end = FRAMES
    for frame in range(1, FRAMES + 1):
        t = (frame - 1) / (FRAMES - 1) if FRAMES > 1 else 0
        a = math.pi * 2 * 0.5 * t
        r = 9.0
        cam.location = (2.5 + r*math.cos(a), 2.0 - r*math.sin(a), 3.5 + 1.5*math.sin(t*math.pi))
        cam.keyframe_insert(data_path="location", frame=frame)

    # Lights
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    bpy.context.object.data.energy = 4.0
    bpy.ops.object.light_add(type="AREA", location=(2.5, 2, 2.8))
    bpy.context.object.data.energy = 300; bpy.context.object.data.size = 5

    # Render
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT_DIR, "frame_")

    t0 = time.time()
    bpy.ops.render.render(animation=True)
    elapsed = time.time() - t0

    pngs = sorted(glob.glob(os.path.join(OUT_DIR, "frame_*.png")))
    result.update({
        "success": True,
        "frames": len(pngs),
        "expected": FRAMES,
        "duration_s": round(elapsed, 1),
        "engine": "CYCLES", "device": "CPU", "samples": 8,
    })
    print(f"RENDERED: {len(pngs)}/{FRAMES} frames in {elapsed:.1f}s")

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print(f"FAILED: {e}")
    write_result()
    sys.exit(1)

write_result()
