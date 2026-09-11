"""PR002 Phase 2 — Import validated GLB, compute bounds, fix visibility, render diagnostic frame."""
import bpy, os, json, math, sys, traceback

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
OUT_JSON = os.path.join(OUT_DIR, "diagnose_result.json")
os.makedirs(OUT_DIR, exist_ok=True)

result = {"success": False}
def write_result():
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    result["object_count"] = len(obs)

    # World-space bounds
    xs, ys, zs = [], [], []
    for o in obs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    bounds = {
        "x": [min(xs), max(xs)],
        "y": [min(ys), max(ys)],
        "z": [min(zs), max(zs)],
    }
    result["bounds"] = {k: [round(v, 3) for v in vv] for k, vv in bounds.items()}
    cx = (bounds["x"][0] + bounds["x"][1]) / 2
    cy = (bounds["y"][0] + bounds["y"][1]) / 2
    cz = (bounds["z"][0] + bounds["z"][1]) / 2
    size = max(bounds["x"][1]-bounds["x"][0],
               bounds["y"][1]-bounds["y"][0],
               bounds["z"][1]-bounds["z"][0])
    result["center"] = [round(cx,3), round(cy,3), round(cz,3)]
    result["scene_size"] = round(size, 3)

    # --- Fix visibility ---
    # 1. Neutral visible material on every mesh
    mat = bpy.data.materials.new("PR002_Neutral")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], mat.node_tree.nodes["Material Output"].inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.85, 0.83, 0.78, 1.0)  # warm light gray
    bsdf.inputs["Roughness"].default_value = 0.7
    for o in obs:
        if o.data.materials:
            o.data.materials.clear()
        o.data.materials.append(mat)
    result["material"] = "PR002_Neutral assigned to all objects"

    # 2. Strong world illumination (bright background so no black void)
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.7, 0.8, 0.9, 1.0)  # sky blue-gray
    bg.inputs["Strength"].default_value = 1.0
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    result["world"] = "bright sky background (strength 1.0)"

    # 3. Sun light for directional shadows
    bpy.ops.object.light_add(type="SUN", location=(cx + size, cy - size, cz + size * 2))
    sun = bpy.context.object
    sun.data.energy = 5.0
    sun.data.angle = 0.2
    result["sun"] = "SUN energy 5.0"

    # 4. Area light for fill
    bpy.ops.object.light_add(type="AREA", location=(cx, cy, cz + size))
    area = bpy.context.object
    area.data.energy = 200.0
    area.data.size = size * 1.5
    result["area"] = "AREA fill energy 200"

    # --- Camera from bounds ---
    scene = bpy.context.scene
    # Exterior elevated 3/4 view: offset camera along +x, +y(depth), +z
    dist = size * 2.2
    cam_loc = (cx + dist * 0.6, cy - dist * 0.9, cz + dist * 0.7)
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.object
    scene.camera = cam
    # Point at scene center
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(cx, cy, cz))
    target = bpy.context.object
    tr = cam.constraints.new(type="TRACK_TO")
    tr.target = target
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Z"
    result["camera_location"] = [round(v, 3) for v in cam_loc]

    # Clip far enough for whole scene
    cam.data.clip_end = size * 20
    result["clip_end"] = size * 20

    # --- Render diagnostic frame ---
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT_DIR, "diagnostic_frame.png")
    bpy.ops.render.render(write_still=True)

    result["success"] = True
    result["frame"] = os.path.join(OUT_DIR, "diagnostic_frame.png")
    print("DIAGNOSTIC RENDER OK")
    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])
    write_result()
    sys.exit(1)

write_result()
