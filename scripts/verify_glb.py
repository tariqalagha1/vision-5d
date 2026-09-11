import struct, json, os, glob

# Find the latest exported GLB
glb_files = glob.glob(r'C:\Users\admin\workspaces\vision-5d\.exports\scene_*.glb')
glb_files.sort(key=os.path.getmtime, reverse=True)
glb = glb_files[0]

print(f"GLB file: {glb}")
print(f"Size: {os.path.getsize(glb)} bytes")

with open(glb, 'rb') as f:
    data = f.read()

magic = struct.unpack_from('<I', data, 0)[0]
version = struct.unpack_from('<I', data, 4)[0]
total = struct.unpack_from('<I', data, 8)[0]
json_len = struct.unpack_from('<I', data, 12)[0]
gltf = json.loads(data[20:20+json_len].rstrip(b' \x00').decode('utf-8'))

meshes = gltf.get('meshes', [])
nodes = gltf.get('nodes', [])
accessors = gltf.get('accessors', [])
prims = sum(len(m.get('primitives', [])) for m in meshes)
total_verts = sum(a['count'] for a in accessors if a.get('type') == 'VEC3')
total_idx = sum(a['count'] for a in accessors if a.get('type') == 'SCALAR')

print(f'Magic: {hex(magic)} (gLTF={hex(magic)==hex(0x46546C67)})')
print(f'GLB version: {version}')
print(f'File size: {len(data)} bytes (declared {total})')
print(f'Meshes: {len(meshes)}')
print(f'Nodes: {len(nodes)}')
print(f'Primitives: {prims}')
print(f'Total vertices: {total_verts}')
print(f'Total indices: {total_idx}')
print(f'Accessors: {len(accessors)}')
print(f'BufferViews: {len(gltf.get("bufferViews", []))}')
print(f'Buffers: {len(gltf.get("buffers", []))}')
