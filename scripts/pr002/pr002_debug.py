"""PR002 debug — explicit camera aim (no constraint), verify visibility, small fast render."""
import bpy, os, json, sys, traceback
from mathutils import Vector

GLB_PATH = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT_DIR = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-002"
os.makedirs(OUT_DIR, exist_ok=True)

result = {"success": False}
try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    xs, ys, zs = [], [], []
    for o in obs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    cx = (min(xs)+max(xs))/2; cy = (min(ys)+max(ys))/2; cz = (min(zs)+max(zs))/2
    result["object_count"] = len(obs)
    result["bounds"] = {"x":[min(xs),max(xs)],"y":[min(ys),max(ys)],"z":[min(zs),max(zs)]}
    result["center"] = [cx, cy, cz]
    print("CENTER", [cx, cy, cz], "bounds", result["bounds"])

    # hide/hide flags check
    result["hidden"] = [o.name for o in obs if o.hide_viewport or o.hide_render]

    # material
    mat = bpy.data.materials.new("Debug_Neutral")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], mat.node_tree.nodes["Material Output"].inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.85, 0.83, 0.78, 1.0)
    for o in obs:
        if o.data.materials:
            o.data.materials.clear()
        o.data.materials.append(mat)

    # world via scene.world directly (robust)
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
    result["world_color"] = list(bg.inputs["Color"].default_value)

    # lights
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 12))
    sun = bpy.context.object
    sun.data.energy = 5.0

    # camera with EXPLICIT aim
    cam_loc = Vector((2.5, -10.0, 6.0))
    target = Vector((cx, cy, 0.8))
    direction = (target - cam_loc).normalized()
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.object
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    cam.data.clip_end = 200.0

    bpy.context.view_layer.update()

    # verify: camera forward (world -Z rotated by camera rotation)
    fwd = cam.matrix_world.to_quaternion() @ Vector((0,0,-1))
    result["camera_loc"] = [round(v,3) for v in cam_loc]
    result["camera_fwd"] = [round(v,3) for v in fwd]
    result["camera_euler"] = [round(v,3) for v in cam.rotation_euler]
    print("CAM LOC", cam_loc, "EULER", cam.rotation_euler)
    print("CAM FWD (should point at target)", fwd, "target dir", direction)

    # render SMALL fast
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT_DIR, "debug_small.png")
    bpy.ops.render.render(write_still=True)

    result["success"] = True
    print("DEBUG RENDER DONE")

except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print("FAILED:", e)
    print(result["traceback"])

with open(os.path.join(OUT_DIR, "debug_result.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
