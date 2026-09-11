"""PR003 — Functional multi-shot property virtual tour.

Scene: fixed_api_glb.glb (living room: floor + 4 walls + sofa + table).
Assigns differentiated materials, validates camera paths, renders 6 shots.

Mode (after --): 'diag' = 1 midpoint frame per shot; 'full' = all frames.
"""
import bpy, os, json, sys, traceback, math
from mathutils import Vector

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"
FPS = 24
RES_X, RES_Y = 1280, 720
SAMPLES = 2
COLLISION_PAD = 0.30   # metres

MODE = "diag"
if "--" in sys.argv:
    MODE = sys.argv[sys.argv.index("--") + 1]

os.makedirs(OUT_DIR, exist_ok=True)
result = {"success": False, "mode": MODE}

# --- Shot plan (derived from bounds: room x[0,5] y[-4,0] z[0,2.7], open back y=-4, furniture ~(2.5,-2.5)) ---
SHOTS = [
    {
        "id": "shot_01", "area": "exterior_context", "name": "Opening context",
        "type": "orbit", "purpose": "Establish whole living-room footprint from outside (elevated sweep)",
        "start": (6.0, -7.0, 4.2), "end": (-1.0, -7.0, 4.2),
        "target": (2.5, -2.0, 1.5), "height": 4.2, "duration": 3.0,
    },
    {
        "id": "shot_02", "area": "entrance_approach", "name": "Approach entrance",
        "type": "approach", "purpose": "Move toward the open entrance side of the room",
        "start": (2.5, -9.0, 2.0), "end": (2.5, -4.6, 1.8),
        "target": (2.5, -2.5, 1.2), "height": 2.0, "duration": 2.5,
    },
    {
        "id": "shot_03", "area": "living_room_primary", "name": "Primary interior walkthrough",
        "type": "walkthrough", "purpose": "Enter the living room at human height and reveal sofa/table",
        "start": (2.5, -4.2, 1.6), "end": (2.5, -3.2, 1.6),
        "target": (2.5, -2.5, 0.9), "height": 1.6, "duration": 2.5,
    },
    {
        "id": "shot_04", "area": "living_room_secondary", "name": "Orbit seating area",
        "type": "orbit", "purpose": "Orbit around the seating group to see sofa from side then front",
        "start": (4.4, -3.0, 1.5), "end": (2.5, -1.2, 1.5),
        "target": (2.5, -2.5, 0.8), "height": 1.5, "duration": 3.0,
    },
    {
        "id": "shot_05", "area": "furniture_feature", "name": "Furniture flyover",
        "type": "orbit", "purpose": "Elevated pass over the sofa/table to read the furniture arrangement",
        "start": (3.5, -3.2, 2.0), "end": (1.5, -2.0, 2.0),
        "target": (2.5, -2.5, 0.8), "height": 2.0, "duration": 2.0,
    },
    {
        "id": "shot_06", "area": "hero_reveal", "name": "Final hero reveal",
        "type": "reveal", "purpose": "Pull up and back to show the whole room in one elevated view",
        "start": (2.5, -2.0, 3.0), "end": (2.5, -9.0, 6.5),
        "target": (2.5, -2.5, 0.5), "height": 6.5, "duration": 3.0,
    },
]

def aim(cam, target):
    d = (Vector(target) - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    result["object_count"] = len(obs)

    # ---- Differentiated materials (Phase 3) ----
    mat_floor = bpy.data.materials.new("M_Floor")
    mat_wall  = bpy.data.materials.new("M_Wall")
    mat_sofa  = bpy.data.materials.new("M_Sofa")
    mat_table = bpy.data.materials.new("M_Table")

    def make_mat(mat, color, rough):
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        if bsdf is None:
            bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
            nt.links.new(bsdf.outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = rough
        return mat

    make_mat(mat_floor, (0.45, 0.32, 0.20, 1.0), 0.6)   # warm wood floor
    make_mat(mat_wall,  (0.90, 0.89, 0.86, 1.0), 0.9)   # off-white walls
    make_mat(mat_sofa,  (0.35, 0.45, 0.55, 1.0), 0.9)   # blue-gray fabric
    make_mat(mat_table, (0.30, 0.20, 0.13, 1.0), 0.5)   # dark wood table

    for o in obs:
        name = o.name.lower()
        # compute object world-center Y to split sofa vs table
        xs = [o.matrix_world @ v.co for v in o.data.vertices]
        cy = sum(v.y for v in xs) / len(xs)
        if o.data.materials:
            o.data.materials.clear()
        if "floor" in name:
            o.data.materials.append(mat_floor)
        elif "wall" in name:
            o.data.materials.append(mat_wall)
        elif "furniture" in name:
            if cy < -2.6:
                o.data.materials.append(mat_sofa)
            else:
                o.data.materials.append(mat_table)
        else:
            o.data.materials.append(mat_wall)

    # ---- Lighting (Phase 4) ----
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

    bpy.ops.object.light_add(type="SUN", location=(10, -10, 12))
    bpy.context.object.data.energy = 5.0
    bpy.context.object.data.angle = 0.2

    bpy.ops.object.light_add(type="AREA", location=(2.5, -2, 6))
    bpy.context.object.data.energy = 250.0
    bpy.context.object.data.size = 9.0

    # ---- Collision validation (Phase 6) ----
    def mesh_aabbs():
        aabbs = []
        for o in obs:
            pts = [o.matrix_world @ v.co for v in o.data.vertices]
            aabbs.append({
                "name": o.name,
                "min": Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
                "max": Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))),
            })
        return aabbs

    aabbs = mesh_aabbs()
    # only walls + furniture are collision hazards (floor is below human height)
    hazards = [a for a in aabbs if ("wall" in a["name"] or "furniture" in a["name"])]

    def collide(pt):
        for h in hazards:
            lo = h["min"] - Vector((COLLISION_PAD, COLLISION_PAD, COLLISION_PAD))
            hi = h["max"] + Vector((COLLISION_PAD, COLLISION_PAD, COLLISION_PAD))
            if lo.x <= pt.x <= hi.x and lo.y <= pt.y <= hi.y and lo.z <= pt.z <= hi.z:
                return h["name"]
        return None

    shot_report = []
    for s in SHOTS:
        start = Vector(s["start"]); end = Vector(s["end"])
        issues = []
        for i in range(21):
            t = i / 20.0
            pt = start.lerp(end, t)
            if pt.z < 0.25:
                issues.append(f"under_floor@{i}")
            hit = collide(pt)
            if hit:
                issues.append(f"collide_{hit}@{i}")
        s["collision_issues"] = issues
        s["valid"] = (len(issues) == 0)
        shot_report.append({"id": s["id"], "valid": s["valid"], "issues": issues})

    result["shots"] = [{"id": s["id"], "name": s["name"], "type": s["type"],
                        "area": s["area"], "duration": s["duration"],
                        "frames": int(s["duration"] * FPS),
                        "valid": s["valid"], "collision_issues": s["collision_issues"]} for s in SHOTS]
    result["shots_generated"] = len(SHOTS)
    result["shots_valid"] = sum(1 for s in SHOTS if s["valid"])
    result["shots_rejected"] = sum(1 for s in SHOTS if not s["valid"])

    # ---- Camera + render ----
    bpy.ops.object.camera_add(location=(0, 0, 3))
    cam = bpy.context.object
    cam.name = "PR003_Camera"
    scene.camera = cam
    cam.data.clip_end = 200.0
    cam.data.clip_start = 0.05

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"

    rendered = []
    for s in SHOTS:
        if not s["valid"]:
            rendered.append({"id": s["id"], "result": "SKIPPED_INVALID"})
            continue
        n = int(s["duration"] * FPS)
        shot_dir = os.path.join(OUT_DIR, "shots", s["id"])
        os.makedirs(shot_dir, exist_ok=True)

        cam.animation_data_clear()
        cam.location = Vector(s["start"]); aim(cam, s["target"])
        cam.keyframe_insert(data_path="location", frame=1)
        cam.keyframe_insert(data_path="rotation_euler", frame=1)
        cam.location = Vector(s["end"]); aim(cam, s["target"])
        cam.keyframe_insert(data_path="location", frame=n)
        cam.keyframe_insert(data_path="rotation_euler", frame=n)

        scene.frame_start = 1
        scene.frame_end = n
        if MODE == "diag":
            scene.frame_current = n // 2
            fp = os.path.join(shot_dir, f"mid_{s['id']}.png")
            scene.render.filepath = fp
            bpy.ops.render.render(write_still=True)
            rendered.append({"id": s["id"], "result": "DIAG", "mid": fp})
        else:
            scene.render.filepath = os.path.join(shot_dir, "frame_")
            bpy.ops.render.render(animation=True)
            rendered.append({"id": s["id"], "result": "RENDERED", "frames": n})

    result["render"] = rendered
    result["success"] = True
    print("PR003 TOUR:", MODE, "done")
    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])

with open(os.path.join(OUT_DIR, "tour_result.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
