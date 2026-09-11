"""Diagnostic: why is the building not visible in render?"""
import bpy
from mathutils import Vector

GLB = r"C:\Users\admin\workspaces\vision-5d\apps\web\RE-SingDetch-FH_AS.glb"

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)

scene = bpy.context.scene
print("OBJECTS in scene:", len(scene.objects))
print("COLLECTIONS:", [c.name for c in bpy.data.collections])
print("VIEW LAYER collections:", [c.name for c in scene.view_layers[0].layer_collection.children] if hasattr(scene.view_layers[0], 'layer_collection') else 'N/A')

meshes = [o for o in scene.objects if o.type=='MESH']
print("MESHES:", len(meshes))
if meshes:
    m = meshes[0]
    print("first mesh:", m.name, "location:", m.location, "hide_render:", m.hide_render, "hide_viewport:", m.hide_viewport)
    print("matrix_world:", [tuple(round(x,1) for x in row) for row in m.matrix_world])
    print("parent:", m.parent)
    print("collections:", [c.name for c in m.users_collection])
    print("vertex count:", len(m.data.vertices))

# check collection visibility
for c in scene.view_layers[0].layer_collection.children:
    print(f"  collection '{c.name}' hide_viewport={c.hide_viewport} exclude={c.exclude}")

# camera
print("scene.camera:", scene.camera)
