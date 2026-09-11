import struct, json, sys, os
sys.path.insert(0, r'C:\Users\admin\workspaces\vision-5d')

from uuid import uuid4
from packages.scene3d.contracts import Scene3D, MeshData, SceneObjectType
from packages.scene3d.glb_export import export_glb, validate_glb

# Build a mesh with NO normals (exactly the case that broke Blender)
v = [0,0,0, 1,0,0, 1,0,1, 0,0,1,  0,1,0, 1,1,0, 1,1,1, 0,1,1]
idx = [0,1,2, 0,2,3, 4,6,5, 4,7,6, 0,4,5, 0,5,1, 1,5,6, 1,6,2, 2,6,7, 2,7,3, 3,7,4, 3,4,0]

mesh = MeshData(
    vertices=v,
    indices=idx,
    object_id=uuid4(),
    object_type=SceneObjectType.WALL_SOLID,
    vertex_count=len(v)//3,
    triangle_count=len(idx)//3,
    # normals intentionally left empty
)

scene = Scene3D(
    scene_id=uuid4(),
    project_id=uuid4(),
    state="CREATED",
    materials=[],
    lights=[],
    meshes=[mesh],
)

glb_bytes = export_glb(scene)
validation = validate_glb(glb_bytes)

print(f"GLB size: {len(glb_bytes)} bytes")
print(f"Validation: {json.dumps(validation, indent=2)}")

# Verify NORMAL accessor count matches POSITION
gltf = json.loads(glb_bytes[20:20+struct.unpack('<I', glb_bytes[12:16])[0]].rstrip(b' \x00').decode('utf-8'))
acc = gltf['accessors']
pos_count = acc[0]['count']
nrm_count = acc[1]['count']
print(f"\nPOSITION accessor count: {pos_count}")
print(f"NORMAL accessor count: {nrm_count}")
print(f"Match: {pos_count == nrm_count}")

assert validation['valid'], f"Validation failed: {validation}"
assert nrm_count == pos_count, "NORMAL count != POSITION count"
print("\n✅ FIX VERIFIED: normals are generated when missing, GLB passes structural validation")
