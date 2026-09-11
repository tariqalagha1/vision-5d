"""PR003 v3 — render remaining shots only (shot_02..shot_06).

Reuses the exact v2 shot plan, materials, lighting, collision validation and
CYCLES render settings. shot_01 (72 frames) is already fully rendered and is
skipped. Renders full frame sequences for shots 02-06 into the same shot dirs.
"""
import bpy, os, json, sys, traceback
from mathutils import Vector

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"
FPS = 24
RES_X, RES_Y = 1280, 720
SAMPLES = 2
COLLISION_PAD = 0.30

# Render only these shots (shot_01 already complete).
ONLY_SHOTS = ["shot_02", "shot_03", "shot_04", "shot_05", "shot_06"]

os.makedirs(OUT_DIR, exist_ok=True)
result = {"success": False, "mode": "full-partial"}

SOFA_C = Vector((2.5, -3.25, 0.7))
TABLE_C = Vector((2.5, -2.0, 0.45))
ROOM_C = Vector((2.5, -2.5, 0.9))

SHOTS = [
    {"id": "shot_01", "area": "exterior_context", "name": "Opening context",
     "type": "orbit", "purpose": "Establish whole room footprint from outside the open side",
     "start": (7.0, -7.0, 2.5), "end": (-2.0, -7.0, 2.5), "target": tuple(ROOM_C), "duration": 3.0},
    {"id": "shot_02", "area": "entrance_approach", "name": "Approach entrance",
     "type": "approach", "purpose": "Move toward the open entrance side at eye level",
     "start": (2.5, -8.5, 1.6), "end": (2.5, -4.6, 1.5), "target": tuple(ROOM_C), "duration": 2.5},
    {"id": "shot_03", "area": "living_walkthrough", "name": "Enter and walk through",
     "type": "walkthrough", "purpose": "Walk along the right side and reveal sofa + table",
     "start": (4.3, -4.4, 1.6), "end": (4.3, -1.6, 1.6), "target": tuple(ROOM_C), "duration": 3.0},
    {"id": "shot_04", "area": "seating_orbit", "name": "Sofa and seating",
     "type": "orbit", "purpose": "Orbit the seating group to see sofa front and table",
     "start": (5.5, -5.5, 1.5), "end": (0.5, -5.5, 1.5), "target": tuple(SOFA_C), "duration": 3.0},
    {"id": "shot_05", "area": "furniture_detail", "name": "Furniture detail",
     "type": "dolly", "purpose": "Dolly toward the sofa to read furniture arrangement",
     "start": (2.5, -6.5, 1.4), "end": (2.5, -4.8, 1.3), "target": tuple(SOFA_C), "duration": 2.5},
    {"id": "shot_06", "area": "hero_reveal", "name": "Final hero reveal",
     "type": "reveal", "purpose": "Pull up and back to show the whole room in one view",
     "start": (2.5, -4.0, 3.5), "end": (2.5, -9.0, 6.0), "target": tuple(ROOM_C), "duration": 3.5},
]

SHOTS = [s for s in SHOTS if s["id"] in ONLY_SHOTS]


def aim(cam, target):
    d = (Vector(target) - cam.location).normalized()
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')


try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    result["object_count"] = len(obs)

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
    hazards = [a for a in aabbs if ("wall" in a["name"] or "furniture" in a["name"])]

    def collide(pt):
        for h in hazards:
            lo = h["min"] - Vector((COLLISION_PAD, COLLISION_PAD, COLLISION_PAD))
            hi = h["max"] + Vector((COLLISION_PAD, COLLISION_PAD, COLLISION_PAD))
            if lo.x <= pt.x <= hi.x and lo.y <= pt.y <= hi.y and lo.z <= pt.z <= hi.z:
                return h["name"]
        return None

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

    result["shots"] = [{"id": s["id"], "name": s["name"], "type": s["type"],
                        "area": s["area"], "duration": s["duration"],
                        "frames": int(s["duration"] * FPS),
                        "valid": s["valid"], "collision_issues": s["collision_issues"]} for s in SHOTS]
    result["shots_generated"] = len(SHOTS)
    result["shots_valid"] = sum(1 for s in SHOTS if s["valid"])
    result["shots_rejected"] = sum(1 for s in SHOTS if not s["valid"])

    bpy.ops.object.camera_add(location=(0, 0, 3))
    cam = bpy.context.object
    cam.name = "PR003_Camera"
    scene.camera = cam
    cam.data.clip_end = 200.0
    cam.data.clip_start = 0.05
    cam.rotation_mode = "QUATERNION"

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
        cam.keyframe_insert(data_path="rotation_quaternion", frame=1)
        cam.location = Vector(s["end"]); aim(cam, s["target"])
        cam.keyframe_insert(data_path="location", frame=n)
        cam.keyframe_insert(data_path="rotation_quaternion", frame=n)

        scene.frame_start = 1
        scene.frame_end = n
        scene.render.filepath = os.path.join(shot_dir, "frame_")
        bpy.ops.render.render(animation=True)
        rendered.append({"id": s["id"], "result": "RENDERED", "frames": n})

    result["render"] = rendered
    result["success"] = True
    print("PR003 TOUR v3: full-partial done")
    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])

with open(os.path.join(OUT_DIR, "tour3_result.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
