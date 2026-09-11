"""PR004 — validate + replan shot_05 and re-render it through the real pipeline.

Reuses the exact v2 material/lighting/camera setup (CYCLES CPU). Imports the
camera_validator module and runs it against the ACTUAL imported scene AABBs:
  1. reproduces the ORIGINAL shot_05 failure (proximity + framing),
  2. validates the REPLACEMENT shot_05,
  3. renders the replacement (60 frames) into the shot_05 dir.
"""
import bpy, os, json, sys, math, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera_validator import validate_path

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"
FPS = 24
RES_X, RES_Y = 1280, 720
SAMPLES = 2

# Original (defective) and replacement shot_05.
ORIGINAL = {"start": (2.5, -6.5, 1.4), "end": (2.5, -4.8, 1.3)}
REPLACEMENT = {
    "id": "shot_05",
    "area": "furniture_detail",
    "name": "Furniture arrangement (sofa + table)",
    "type": "dolly",
    "purpose": "Elevated dolly over the seating to show the full sofa+table arrangement with the table visible in front of the sofa",
    "start": (2.5, -8.5, 4.6),
    "end": (2.5, -7.5, 4.3),
    "target": (2.5, -2.0, 0.72),  # table area, so view clears the sofa backrest
    "duration": 2.5,
}

result = {"success": False, "mode": "pr004-repair"}

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    obs = [o for o in bpy.data.objects if o.type == "MESH"]

    # --- materials / lighting (identical to pr003 v2) ---
    def make_mat(name, color, rough):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            m.node_tree.links.new(bsdf.outputs["BSDF"], m.node_tree.nodes["Material Output"].inputs["Surface"])
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = rough
        return m

    mat_floor = make_mat("M_Floor", (0.45, 0.32, 0.20, 1.0), 0.6)
    mat_wall = make_mat("M_Wall", (0.90, 0.89, 0.86, 1.0), 0.9)
    mat_sofa = make_mat("M_Sofa", (0.35, 0.45, 0.55, 1.0), 0.9)
    mat_table = make_mat("M_Table", (0.30, 0.20, 0.13, 1.0), 0.5)
    for o in obs:
        n = o.name.lower()
        xs = [o.matrix_world @ v.co for v in o.data.vertices]
        cy = sum(v.y for v in xs) / len(xs)
        if o.data.materials:
            o.data.materials.clear()
        if "floor" in n:
            o.data.materials.append(mat_floor)
        elif "wall" in n:
            o.data.materials.append(mat_wall)
        elif "furniture" in n:
            o.data.materials.append(mat_sofa if cy < -2.6 else mat_table)
        else:
            o.data.materials.append(mat_wall)

    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.6, 0.7, 0.9, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 12))
    bpy.context.object.data.energy = 5.0
    bpy.context.object.data.angle = 0.2
    bpy.ops.object.light_add(type="AREA", location=(2.5, -2, 6))
    bpy.context.object.data.energy = 250.0
    bpy.context.object.data.size = 9.0

    # --- generalized geometry AABBs from the actual scene ---
    def obj_aabbs(name_substr):
        out = []
        for o in obs:
            if name_substr not in o.name.lower():
                continue
            pts = [o.matrix_world @ v.co for v in o.data.vertices]
            lo = (min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))
            hi = (max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))
            out.append((lo, hi))
        return out

    furniture = obj_aabbs("furniture")
    # combined arrangement AABB = union of furniture
    lo = (min(a[0][0] for a in furniture), min(a[0][1] for a in furniture), min(a[0][2] for a in furniture))
    hi = (max(a[1][0] for a in furniture), max(a[1][1] for a in furniture), max(a[1][2] for a in furniture))
    target_aabb = (lo, hi)

    # --- camera + FOV ---
    bpy.ops.object.camera_add(location=(0, 0, 3))
    cam = bpy.context.object
    cam.name = "PR004_Camera"
    scene.camera = cam
    cam.data.clip_end = 200.0
    cam.data.clip_start = 0.05
    cam.data.lens = 50.0
    cam.data.sensor_width = 36.0
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.rotation_mode = "QUATERNION"
    hfov = 2 * math.atan(cam.data.sensor_width / (2.0 * cam.data.lens))
    aspect = RES_X / RES_Y
    vfov = 2 * math.atan(math.tan(hfov / 2.0) / aspect)
    hfov_half = math.degrees(hfov / 2.0)
    vfov_half = math.degrees(vfov / 2.0)

    # --- validate original vs replacement against the real scene AABBs ---
    r_orig = validate_path(ORIGINAL["start"], ORIGINAL["end"], furniture,
                           target_aabb, hfov_half, vfov_half)
    r_repl = validate_path(REPLACEMENT["start"], REPLACEMENT["end"], furniture,
                           target_aabb, hfov_half, vfov_half)
    result["fov"] = {"hfov_half_deg": round(hfov_half, 2), "vfov_half_deg": round(vfov_half, 2)}
    result["target_aabb"] = target_aabb
    result["furniture_meshes"] = len(furniture)
    result["original_shot_05"] = r_orig
    result["replacement_shot_05"] = r_repl
    result["original_rejected"] = not r_orig["valid"]
    result["replacement_accepted"] = r_repl["valid"]

    # --- render the replacement shot_05 ---
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"

    n = int(REPLACEMENT["duration"] * FPS)
    shot_dir = os.path.join(OUT_DIR, "shots", "shot_05")
    os.makedirs(shot_dir, exist_ok=True)

    def aim(c, target):
        d = (__import__("mathutils").Vector(target) - c.location).normalized()
        c.rotation_quaternion = d.to_track_quat('-Z', 'Y')

    cam.animation_data_clear()
    cam.location = __import__("mathutils").Vector(REPLACEMENT["start"])
    aim(cam, REPLACEMENT["target"])
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_quaternion", frame=1)
    cam.location = __import__("mathutils").Vector(REPLACEMENT["end"])
    aim(cam, REPLACEMENT["target"])
    cam.keyframe_insert(data_path="location", frame=n)
    cam.keyframe_insert(data_path="rotation_quaternion", frame=n)

    scene.frame_start = 1
    scene.frame_end = n
    scene.render.filepath = os.path.join(shot_dir, "frame_")
    bpy.ops.render.render(animation=True)
    result["render"] = {"shot": "shot_05", "result": "RENDERED", "frames": n}
    result["success"] = True
    print("PR004 done")
    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])

with open(os.path.join(OUT_DIR, "pr004_result.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
