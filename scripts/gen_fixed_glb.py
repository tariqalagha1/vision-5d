"""Generate a GLB using the FIXED export_glb (with normals) and save it for Blender import."""
import sys, os, json, hashlib
sys.path.insert(0, r'C:\Users\admin\workspaces\vision-5d')

from uuid import uuid4
from packages.scene3d.contracts import Scene3D, MeshData, SceneObjectType
from packages.scene3d.glb_export import export_glb, validate_glb

# Mirror the pipeline's geometry: 5 walls (floor + 4 walls) + sofa (4 components) + table (5 components)
room_width, room_depth, wall_height = 5.0, 4.0, 2.7

walls = [
    {"id": "floor", "type": "floor", "b": {"x": 0, "y": 0, "z": 0, "w": room_width, "d": room_depth, "h": 0.1}},
    {"id": "wall_n", "type": "wall", "b": {"x": 0, "y": 0, "z": 0, "w": room_width, "d": 0.2, "h": wall_height}},
    {"id": "wall_s", "type": "wall", "b": {"x": 0, "y": room_depth-0.2, "z": 0, "w": room_width, "d": 0.2, "h": wall_height}},
    {"id": "wall_e", "type": "wall", "b": {"x": room_width-0.2, "y": 0, "z": 0, "w": 0.2, "d": room_depth, "h": wall_height}},
    {"id": "wall_w", "type": "wall", "b": {"x": 0, "y": 0, "z": 0, "w": 0.2, "d": room_depth, "h": wall_height}},
]

sofa_w, sofa_d, seat_h = 2.0, 0.9, 0.4
sofa_x = room_width/2 - sofa_w/2
sofa_z = room_depth - 0.3 - sofa_d
furniture = [
    {"id": "sofa_seat", "type": "sofa_component", "b": {"x": sofa_x, "y": 0.1, "z": sofa_z, "w": sofa_w, "d": sofa_d, "h": seat_h}},
    {"id": "sofa_backrest", "type": "sofa_component", "b": {"x": sofa_x, "y": 0.5, "z": sofa_z, "w": sofa_w, "d": 0.15, "h": 0.7}},
    {"id": "sofa_armrest_left", "type": "sofa_component", "b": {"x": sofa_x, "y": 0.5, "z": sofa_z, "w": 0.15, "d": sofa_d, "h": 0.6}},
    {"id": "sofa_armrest_right", "type": "sofa_component", "b": {"x": sofa_x+sofa_w-0.15, "y": 0.5, "z": sofa_z, "w": 0.15, "d": sofa_d, "h": 0.6}},
]
table_x, table_z = room_width/2 - 0.6, room_depth/2 - 0.4
furniture.append({"id": "table_top", "type": "table_component", "b": {"x": table_x, "y": 0.7, "z": table_z, "w": 1.2, "d": 0.8, "h": 0.05}})
for li, (lx, lz) in enumerate([(0.05,0.05),(1.05,0.05),(0.05,0.65),(1.05,0.65)]):
    furniture.append({"id": f"table_leg_{li}", "type": "table_component", "b": {"x": table_x+lx, "y": 0.1, "z": table_z+lz, "w": 0.08, "d": 0.08, "h": 0.6}})

def box_vertices(b):
    x, y, z = b["x"], b["y"], b["z"]
    w, d, h = b["w"], b["d"], b["h"]
    return [
        x, y, z,   x+w, y, z,   x+w, y, z+d,   x, y, z+d,
        x, y+h, z, x+w, y+h, z, x+w, y+h, z+d, x, y+h, z+d,
    ]

BOX_IDX = [0,1,2, 0,2,3, 4,6,5, 4,7,6, 0,4,5, 0,5,1, 1,5,6, 1,6,2, 2,6,7, 2,7,3, 3,7,4, 3,4,0]

mesh_list = []
for obj in walls + furniture:
    b = obj["b"]
    v = box_vertices(b)
    sotype = ("floor_slab" if "floor" in obj["type"] else
              "wall_solid" if "wall" in obj["type"] else "furniture_instance")
    mesh_list.append(MeshData(
        vertices=v, indices=list(BOX_IDX),
        object_id=uuid4(), object_type=SceneObjectType(sotype),
        vertex_count=len(v)//3, triangle_count=len(BOX_IDX)//3,
        # normals LEFT EMPTY — this is the exact case the fix must handle
    ))

scene = Scene3D(scene_id=uuid4(), project_id=uuid4(), state="CREATED",
                materials=[], lights=[], meshes=mesh_list)

glb_bytes = export_glb(scene)
validation = validate_glb(glb_bytes)

out = r'C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb'
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'wb') as f:
    f.write(glb_bytes)

print(json.dumps({
    "glb_path": out,
    "size_bytes": len(glb_bytes),
    "sha256": hashlib.sha256(glb_bytes).hexdigest(),
    "meshes": len(mesh_list),
    "valid": validation["valid"],
    "validation": validation,
}, indent=2))
