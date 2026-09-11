import bpy, os, json, hashlib, sys, traceback

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\.exports\scene_df033e3f-521c-42b1-99a9-0de49606ea0c.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\api_glb_verify"
OUT_JSON = os.path.join(OUT_DIR, "result.json")

result = {"success": False, "error": "", "traceback": ""}
os.makedirs(OUT_DIR, exist_ok=True)

def write_result():
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    result["objects"] = len(obs)
    result["meshes"] = len(bpy.data.meshes)
    total_verts = sum(len(o.data.vertices) for o in obs)
    total_polys = sum(len(o.data.polygons) for o in obs)
    result["vertices"] = total_verts
    result["polygons"] = total_polys

    # Bounds
    xs, ys, zs = [], [], []
    for o in obs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    result["bounds"] = {
        "x": [round(min(xs),2), round(max(xs),2)],
        "y": [round(min(ys),2), round(max(ys),2)],
        "z": [round(min(zs),2), round(max(zs),2)],
    }

    # Camera
    bpy.ops.object.camera_add(location=(8, -8, 5))
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(2.5, 2.0, 1.5))
    t = bpy.context.object
    tr = cam.constraints.new(type="TRACK_TO")
    tr.target = t; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"

    # Lights
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    bpy.context.object.data.energy = 4.0
    bpy.ops.object.light_add(type="AREA", location=(2.5, 2, 2.8))
    bpy.context.object.data.energy = 300; bpy.context.object.data.size = 5

    # Render
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT_DIR, "diagnostic.png")
    bpy.ops.render.render(write_still=True)

    result["success"] = True
    result["frame"] = os.path.join(OUT_DIR, "diagnostic.png")
    print(f"RENDERED: {result['objects']} objects, {total_verts} verts, {total_polys} polys")
    print(f"BOUNDS: {result['bounds']}")

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print(f"FAILED: {e}")
    print(result["traceback"])
    write_result()
    sys.exit(1)

write_result()
