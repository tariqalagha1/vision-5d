"""
Vision 5D — Authoritative Blender Render Script
Handles GLB import, engine resolution, rendering with truthful exit codes.
Designed for Windows headless Blender 5.2.0+ with CYCLES_CPU fallback.

Usage: blender.exe --background --python this_script.py
"""
import bpy, os, sys, json, hashlib, math, time, traceback, glob

# ── Configuration (overridden by environment or command-line) ──
GLB_PATH = os.environ.get("V5D_GLB_PATH", "")
RENDER_DIR = os.environ.get("V5D_RENDER_DIR", "")
OUT_JSON = os.environ.get("V5D_OUT_JSON", "")
RENDER_ENGINE = os.environ.get("V5D_RENDER_ENGINE", "CYCLES")
RENDER_DEVICE = os.environ.get("V5D_RENDER_DEVICE", "CPU")
RENDER_SAMPLES = int(os.environ.get("V5D_RENDER_SAMPLES", "32"))
RENDER_FRAMES = int(os.environ.get("V5D_RENDER_FRAMES", "150"))
RENDER_WIDTH = int(os.environ.get("V5D_RENDER_WIDTH", "1280"))
RENDER_HEIGHT = int(os.environ.get("V5D_RENDER_HEIGHT", "720"))
RENDER_FPS = int(os.environ.get("V5D_RENDER_FPS", "30"))
RENDER_DENOISE = os.environ.get("V5D_RENDER_DENOISE", "true").lower() == "true"

EXIT_SUCCESS = 0
EXIT_GLB_IMPORT_FAILED = 10
EXIT_ENGINE_NOT_FOUND = 11
EXIT_RENDER_FAILED = 12
EXIT_INCOMPLETE_FRAMES = 13
EXIT_UNHANDLED = 99

# ── Truthful result tracking ──
result = {
    "success": False,
    "exit_code": EXIT_UNHANDLED,
    "error": "",
    "traceback": "",
    "glb_path": "",
    "glb_sha256": "",
    "engine_requested": RENDER_ENGINE,
    "engine_resolved": "",
    "device": RENDER_DEVICE,
    "samples": RENDER_SAMPLES,
    "expected_frames": RENDER_FRAMES,
    "actual_frames": 0,
    "failed_frames": 0,
    "missing_frames": [],
    "render_duration_s": 0.0,
    "first_frame_size": 0,
    "total_frame_size": 0,
    "objects_imported": 0,
    "meshes_imported": 0,
    "vertices_imported": 0,
    "bounds": None,
    "available_engines": [],
    "cycles_devices": {},
    "eevee_headless_crashed": False,
}

def write_result():
    """Write structured result JSON, always."""
    try:
        if OUT_JSON:
            os.makedirs(os.path.dirname(OUT_JSON) or ".", exist_ok=True)
            with open(OUT_JSON, "w") as f:
                json.dump(result, f, indent=2, default=str)
    except Exception:
        pass  # Best-effort

def fail(exit_code, error_msg):
    """Set failure state and exit with non-zero code."""
    result["success"] = False
    result["exit_code"] = exit_code
    result["error"] = error_msg
    write_result()
    print(f"FATAL [{exit_code}]: {error_msg}", file=sys.stderr)
    sys.exit(exit_code)

# ── Top-level exception boundary ──
try:
    # ── Validate inputs ──
    if not GLB_PATH:
        fail(EXIT_GLB_IMPORT_FAILED, "V5D_GLB_PATH not set")
    if not os.path.exists(GLB_PATH):
        fail(EXIT_GLB_IMPORT_FAILED, f"GLB file not found: {GLB_PATH}")
    if not RENDER_DIR:
        fail(EXIT_GLB_IMPORT_FAILED, "V5D_RENDER_DIR not set")

    result["glb_path"] = os.path.abspath(GLB_PATH)
    with open(GLB_PATH, "rb") as f:
        result["glb_sha256"] = hashlib.sha256(f.read()).hexdigest()

    os.makedirs(RENDER_DIR, exist_ok=True)
    print(f"GLB: {result['glb_path']} (SHA-256: {result['glb_sha256']})")
    print(f"Render: {RENDER_WIDTH}x{RENDER_HEIGHT}, {RENDER_FRAMES} frames, {RENDER_FPS} FPS")
    print(f"Engine requested: {RENDER_ENGINE}, Device: {RENDER_DEVICE}, Samples: {RENDER_SAMPLES}")

    # ── Clear and import GLB ──
    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    except RuntimeError as e:
        fail(EXIT_GLB_IMPORT_FAILED, f"GLB import failed: {e}")

    obs = bpy.data.objects
    meshes = bpy.data.meshes
    result["objects_imported"] = len(obs)
    result["meshes_imported"] = len(meshes)
    mesh_objs = [ob for ob in obs if ob.type == "MESH"]
    if mesh_objs:
        bbox = [mesh_objs[0].matrix_world @ v.co for v in mesh_objs[0].data.vertices]
        xs = [v.x for v in bbox]; ys = [v.y for v in bbox]; zs = [v.z for v in bbox]
        result["bounds"] = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]}
        result["vertices_imported"] = len(mesh_objs[0].data.vertices)
        print(f"Imported: {len(obs)} objects, {len(meshes)} meshes, {result['vertices_imported']} vertices")
        print(f"Bounds: {result['bounds']}")
    else:
        fail(EXIT_GLB_IMPORT_FAILED, "No mesh objects found in imported GLB")

    # ── Engine resolution ──
    scene = bpy.context.scene

    # Get available engines by testing
    available = []
    for eng_candidate in ["BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"]:
        try:
            old = scene.render.engine
            scene.render.engine = eng_candidate
            available.append(eng_candidate)
        except Exception:
            pass
    scene.render.engine = old  # restore
    result["available_engines"] = available
    print(f"Available engines: {available}")

    resolved_engine = RENDER_ENGINE
    engine_fallback_reason = ""

    if RENDER_ENGINE == "BLENDER_EEVEE_NEXT":
        if "BLENDER_EEVEE" in available:
            resolved_engine = "BLENDER_EEVEE"
            engine_fallback_reason = "BLENDER_EEVEE_NEXT not found, resolved to BLENDER_EEVEE"
        else:
            fail(EXIT_ENGINE_NOT_FOUND, "BLENDER_EEVEE_NEXT not available and BLENDER_EEVEE not found")
    elif RENDER_ENGINE not in available:
        # Fallback to CYCLES
        if "CYCLES" in available:
            resolved_engine = "CYCLES"
            engine_fallback_reason = f"{RENDER_ENGINE} not available, fell back to CYCLES"
        else:
            fail(EXIT_ENGINE_NOT_FOUND, f"Engine {RENDER_ENGINE} not available and no fallback")

    result["engine_resolved"] = resolved_engine
    if engine_fallback_reason:
        result["engine_fallback_reason"] = engine_fallback_reason
        print(f"Engine fallback: {engine_fallback_reason}")

    scene.render.engine = resolved_engine

    # ── CYCLES device configuration ──
    if resolved_engine == "CYCLES":
        cycles_devices = {}
        try:
            cprefs = bpy.context.preferences.addons["cycles"].preferences
            cprefs.refresh_devices()
            for d in cprefs.devices:
                cycles_devices[d.name] = d.type
        except Exception:
            pass
        result["cycles_devices"] = cycles_devices
        print(f"Cycles devices: {cycles_devices}")

        # Check for GPU
        has_gpu = any(t in ("CUDA", "OPTIX", "HIP", "ONEAPI") for t in cycles_devices.values())

        if RENDER_DEVICE == "GPU" and has_gpu:
            scene.cycles.device = "GPU"
            result["device"] = "GPU"
        else:
            scene.cycles.device = "CPU"
            result["device"] = "CPU"
            if RENDER_DEVICE == "GPU" and not has_gpu:
                result["gpu_fallback_reason"] = "GPU requested but no CUDA/OPTIX/HIP devices found"

        scene.cycles.samples = RENDER_SAMPLES
        if RENDER_DENOISE:
            scene.cycles.use_denoising = True
    print(f"Engine: {resolved_engine}, Device: {result['device']}, Samples: {RENDER_SAMPLES}, Denoise: {RENDER_DENOISE}")

    # ── EEVEE headless recheck ──
    if resolved_engine == "BLENDER_EEVEE":
        # Attempt a single-frame EEVEE render to verify headless compatibility
        try:
            scene.render.resolution_x = RENDER_WIDTH
            scene.render.resolution_y = RENDER_HEIGHT
            scene.render.image_settings.file_format = "PNG"
            test_path = os.path.join(RENDER_DIR, "_eevee_test.png")
            scene.render.filepath = test_path
            bpy.ops.render.render(write_still=True)
            if os.path.exists(test_path):
                os.remove(test_path)
                print("EEVEE headless: OK")
            else:
                print("EEVEE headless: frame not written (likely crash)")
                result["eevee_headless_crashed"] = True
        except Exception as e:
            result["eevee_headless_crashed"] = True
            result["eevee_crash_error"] = str(e)
            print(f"EEVEE headless crash detected: {e}")

        if result.get("eevee_headless_crashed"):
            if "CYCLES" in available:
                resolved_engine = "CYCLES"
                scene.render.engine = "CYCLES"
                scene.cycles.device = "CPU"
                scene.cycles.samples = RENDER_SAMPLES
                if RENDER_DENOISE:
                    scene.cycles.use_denoising = True
                result["engine_resolved"] = "CYCLES"
                result["device"] = "CPU"
                result["eevee_headless_fallback"] = "EEVEE_HEADLESS_UNAVAILABLE_ON_CURRENT_RUNTIME"
                print("Falling back to CYCLES_CPU after EEVEE headless crash")

    # ── Setup camera, lights, animation ──
    bpy.ops.object.camera_add(location=(10, -10, 5))
    cam = bpy.context.object
    cam.name = "CinematicCamera"
    scene.camera = cam

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(2.5, 3.0, 1.5))
    target = bpy.context.object
    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    scene.frame_start = 1
    scene.frame_end = RENDER_FRAMES

    for frame in range(1, RENDER_FRAMES + 1):
        t = (frame - 1) / (RENDER_FRAMES - 1) if RENDER_FRAMES > 1 else 0
        a = math.pi * 2 * 0.5 * t
        r = 9.0
        cx, cy = 2.5, 3.0
        cam.location = (cx + r * math.cos(a), cy - r * math.sin(a), 3.5 + 1.5 * math.sin(t * math.pi))
        cam.keyframe_insert(data_path="location", frame=frame)

    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    bpy.context.object.data.energy = 4.0
    bpy.context.object.data.angle = 0.5

    bpy.ops.object.light_add(type="AREA", location=(2.5, 3, 2.8))
    bpy.context.object.data.energy = 300
    bpy.context.object.data.size = 5

    # ── Render settings ──
    scene.render.resolution_x = RENDER_WIDTH
    scene.render.resolution_y = RENDER_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(RENDER_DIR, "frame_")

    # ── Render ──
    print(f"Rendering {RENDER_FRAMES} frames ({resolved_engine}, {result['device']}, {RENDER_SAMPLES} samples)...")
    t0 = time.time()

    try:
        bpy.ops.render.render(animation=True)
    except Exception as e:
        fail(EXIT_RENDER_FAILED, f"Render exception: {e}")

    elapsed = time.time() - t0
    result["render_duration_s"] = round(elapsed, 1)

    # ── Validate frame output ──
    pngs = sorted(glob.glob(os.path.join(RENDER_DIR, "frame_*.png")))
    result["actual_frames"] = len(pngs)
    result["missing_frames"] = []

    for i in range(1, RENDER_FRAMES + 1):
        expected = os.path.join(RENDER_DIR, f"frame_{i:04d}.png")
        if not os.path.exists(expected):
            result["missing_frames"].append(i)

    result["failed_frames"] = len(result["missing_frames"])

    if pngs:
        result["first_frame_size"] = os.path.getsize(pngs[0])
        result["total_frame_size"] = sum(os.path.getsize(p) for p in pngs)

    print(f"Rendered: {result['actual_frames']}/{RENDER_FRAMES} frames in {elapsed:.1f}s")
    if result["missing_frames"]:
        print(f"MISSING FRAMES: {result['missing_frames']}")

    if result["failed_frames"] > 0:
        fail(EXIT_INCOMPLETE_FRAMES,
             f"Incomplete render: {result['failed_frames']} frames missing of {RENDER_FRAMES}")

    result["success"] = True
    result["exit_code"] = EXIT_SUCCESS
    write_result()
    print(f"SUCCESS: {result['actual_frames']} frames rendered")

except SystemExit:
    # Already handled by fail()
    raise

except Exception as e:
    # Unhandled exception boundary
    result["success"] = False
    result["exit_code"] = EXIT_UNHANDLED
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    write_result()
    print(f"FATAL UNHANDLED: {e}", file=sys.stderr)
    print(result["traceback"], file=sys.stderr)
    sys.exit(EXIT_UNHANDLED)
