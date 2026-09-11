"""Independent GLB validation: import into Blender and report object/mesh/triangle counts."""
import bpy
import sys

glb = sys.argv[sys.argv.index("--") + 1]

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

result = {"file": glb, "imported": False, "objects": 0, "meshes": 0, "triangles": 0,
          "vertices": 0, "bounds": None, "error": None}

try:
    bpy.ops.import_scene.gltf(filepath=glb)
    result["imported"] = True
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    result["objects"] = len(objs)
    total_tris = 0
    total_verts = 0
    for o in objs:
        m = o.to_mesh()
        total_tris += sum(len(p.vertices) - 2 for p in m.polygons) if len(m.polygons) else 0
        total_verts += len(m.vertices)
    result["meshes"] = len(objs)
    result["triangles"] = total_tris
    result["vertices"] = total_verts
    # Overall bounds
    xs = []; ys = []; zs = []
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ v
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    if xs:
        result["bounds"] = {
            "x": [round(min(xs),1), round(max(xs),1)],
            "y": [round(min(ys),1), round(max(ys),1)],
            "z": [round(min(zs),1), round(max(zs),1)],
        }
except Exception as e:
    result["error"] = f"{type(e).__name__}: {e}"

import json
print("BLENDER_GLB_RESULT " + json.dumps(result))
