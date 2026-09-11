"""
Vision 5D — GLB Export Engine
Generates binary glTF 2.0 (GLB) files from Scene3D mesh data.
Minimal, zero-dependency binary writer.
"""
import struct, json as _json, hashlib
from uuid import UUID
from typing import Optional
from packages.scene3d.contracts import Scene3D, MeshData, Material


def export_glb(scene: Scene3D) -> bytes:
    """Export a Scene3D to a GLB binary buffer."""
    # Build glTF JSON
    gltf = _build_gltf_json(scene)
    json_bytes = _json.dumps(gltf, separators=(',', ':')).encode('utf-8')

    # Build binary buffer (vertex + index data interleaved per mesh)
    buffer_chunks = []
    buffer_views = []
    accessors = []
    byte_offset = 0

    for mi, mesh in enumerate(scene.meshes):
        # Authoritative vertex/index counts come from the actual packed data,
        # NOT the mesh.vertex_count/triangle_count fields (which are stale for
        # some object types). This guarantees POSITION/NORMAL/INDEX accessor
        # counts are mutually consistent.
        v_count = len(mesh.vertices) // 3
        if v_count == 0:
            continue

        # Vertices: float32
        v_data = struct.pack(f'<{len(mesh.vertices)}f', *mesh.vertices)
        v_padded = _pad_to_4(v_data)
        v_len = len(v_padded)
        buffer_views.append({"buffer": 0, "byteOffset": byte_offset, "byteLength": v_len, "target": 34962})
        accessors.append({
            "bufferView": mi * 3, "componentType": 5126, "count": v_count,
            "type": "VEC3", "max": _max_chunk(mesh.vertices, 3), "min": _min_chunk(mesh.vertices, 3),
        })
        buffer_chunks.append(v_padded)
        byte_offset += v_len

        # Normals: float32 — always emit normals with count == vertex count
        normals = mesh.normals
        if not normals or len(normals) != v_count * 3:
            normals = _compute_flat_normals(mesh.vertices, mesh.indices)
        n_data = struct.pack(f'<{len(normals)}f', *normals)
        n_padded = _pad_to_4(n_data)
        n_len = len(n_padded)
        buffer_views.append({"buffer": 0, "byteOffset": byte_offset, "byteLength": n_len, "target": 34962})
        accessors.append({
            "bufferView": mi * 3 + 1, "componentType": 5126, "count": len(normals) // 3,
            "type": "VEC3",
        })
        buffer_chunks.append(n_padded)
        byte_offset += n_len

        # Indices: uint16 or uint32
        max_idx = max(mesh.indices) if mesh.indices else 0
        if max_idx <= 65535:
            i_fmt = 'H'
            i_ct = 5123
            i_pack = f'<{len(mesh.indices)}H'
        else:
            i_fmt = 'I'
            i_ct = 5125
            i_pack = f'<{len(mesh.indices)}I'
        i_data = struct.pack(i_pack, *mesh.indices) if mesh.indices else b''
        i_padded = _pad_to_4(i_data)
        i_len = len(i_padded)
        buffer_views.append({"buffer": 0, "byteOffset": byte_offset, "byteLength": i_len, "target": 34963})
        accessors.append({
            "bufferView": mi * 3 + 2, "componentType": i_ct, "count": len(mesh.indices),
            "type": "SCALAR",
        })
        buffer_chunks.append(i_padded)
        byte_offset += i_len

    bin_buffer = b''.join(buffer_chunks)

    # Inject accessors, bufferViews, and buffer byteLength into the glTF JSON
    # (they were built above but _build_gltf_json returned empty placeholders)
    gltf["accessors"] = accessors
    gltf["bufferViews"] = buffer_views
    gltf["buffers"][0]["byteLength"] = len(bin_buffer)
    json_bytes = _json.dumps(gltf, separators=(',', ':')).encode('utf-8')

    # Assemble GLB
    json_chunk = _pad_json_to_4(json_bytes)
    bin_chunk = _pad_to_4(bin_buffer)

    header = struct.pack('<I', 0x46546C67)  # magic 'glTF'
    header += struct.pack('<I', 2)           # version 2
    # Total = header(12) + json_header(8) + json_chunk + bin_header(8) + bin_chunk
    total_len = 12 + 8 + len(json_chunk) + (8 + len(bin_chunk) if bin_chunk else 0)
    header += struct.pack('<I', total_len)

    # JSON chunk — chunkLength is the PADDED length (glTF requires chunks aligned to 4 bytes)
    json_header = struct.pack('<I', len(json_chunk))
    json_header += struct.pack('<I', 0x4E4F534A)  # 'JSON'

    # BIN chunk — chunkLength is the PADDED length; buffer.byteLength (in glTF JSON)
    # is the UNPADDED data length, which readers use to slice past trailing zeros.
    bin_header = b''
    if bin_chunk:
        bin_header = struct.pack('<I', len(bin_chunk))
        bin_header += struct.pack('<I', 0x004E4942)  # 'BIN\0'

    return header + json_header + json_chunk + bin_header + bin_chunk


def _build_gltf_json(scene: Scene3D) -> dict:
    """Build the glTF 2.0 JSON structure."""
    meshes = []
    nodes = []
    materials = []

    for mi, mesh in enumerate(scene.meshes):
        primitives = [{
            "attributes": {
                "POSITION": mi * 3,
                "NORMAL": mi * 3 + 1,
            },
            "indices": mi * 3 + 2,
        }]
        if mesh.material_id:
            mat_idx = _find_material_index(scene, mesh.material_id)
            if mat_idx >= 0:
                primitives[0]["material"] = mat_idx

        meshes.append({"primitives": primitives, "name": mesh.object_type.value})
        nodes.append({"mesh": mi, "name": mesh.object_type.value})

    # Materials
    for mat in scene.materials:
        r, g, b, a = mat.base_color
        materials.append({
            "pbrMetallicRoughness": {
                "baseColorFactor": [r, g, b, a],
                "metallicFactor": mat.metallic,
                "roughnessFactor": mat.roughness,
            },
            "name": mat.name,
            "alphaMode": "BLEND" if a < 1.0 else "OPAQUE",
        })

    gltf = {
        "asset": {"version": "2.0", "generator": "Vision5D-Phase4"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": [],
        "bufferViews": [],
        "buffers": [{"byteLength": 0}],  # filled later
    }
    return gltf


def _find_material_index(scene: Scene3D, mat_id: UUID) -> int:
    for i, m in enumerate(scene.materials):
        if m.material_id == mat_id:
            return i
    return -1


def _pad_to_4(data: bytes) -> bytes:
    rem = len(data) % 4
    if rem:
        return data + b'\x00' * (4 - rem)
    return data


def _pad_json_to_4(data: bytes) -> bytes:
    """Pad JSON chunk with spaces (0x20) per glTF spec — NOT NUL bytes."""
    rem = len(data) % 4
    if rem:
        return data + b' ' * (4 - rem)
    return data


def _compute_flat_normals(vertices: list[float], indices: list[int]) -> list[float]:
    """Compute per-vertex normals by accumulating face normals (flat shading).

    Returns a flat list of [nx,ny,nz, ...] with one normal per vertex.
    glTF requires each POSITION accessor to have a matching NORMAL accessor
    of the same count; Blender rejects NORMAL accessors with count 0.
    """
    v_count = len(vertices) // 3
    normals = [0.0] * (v_count * 3)

    for i in range(0, len(indices) - 2, 3):
        i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
        if i0 >= v_count or i1 >= v_count or i2 >= v_count:
            continue
        ax, ay, az = vertices[i0*3], vertices[i0*3+1], vertices[i0*3+2]
        bx, by, bz = vertices[i1*3], vertices[i1*3+1], vertices[i1*3+2]
        cx, cy, cz = vertices[i2*3], vertices[i2*3+1], vertices[i2*3+2]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = (nx * nx + ny * ny + nz * nz) ** 0.5
        if length > 1e-12:
            nx, ny, nz = nx / length, ny / length, nz / length
        for vi in (i0, i1, i2):
            normals[vi*3] += nx
            normals[vi*3+1] += ny
            normals[vi*3+2] += nz

    # Normalize accumulated normals
    for j in range(v_count):
        nx, ny, nz = normals[j*3], normals[j*3+1], normals[j*3+2]
        length = (nx * nx + ny * ny + nz * nz) ** 0.5
        if length > 1e-12:
            normals[j*3], normals[j*3+1], normals[j*3+2] = nx / length, ny / length, nz / length
        else:
            normals[j*3], normals[j*3+1], normals[j*3+2] = 0.0, 0.0, 1.0
    return normals


def _max_chunk(data: list[float], stride: int) -> list[float]:
    result = [float('-inf')] * stride
    for i in range(0, len(data), stride):
        for j in range(stride):
            if i + j < len(data):
                result[j] = max(result[j], data[i + j])
    return result


def _min_chunk(data: list[float], stride: int) -> list[float]:
    result = [float('inf')] * stride
    for i in range(0, len(data), stride):
        for j in range(stride):
            if i + j < len(data):
                result[j] = min(result[j], data[i + j])
    return result


def validate_glb(glb_bytes: bytes) -> dict:
    """Validate a GLB buffer and return metadata."""
    if len(glb_bytes) < 12:
        return {"valid": False, "error": "Too short for GLB header"}
    magic = struct.unpack('<I', glb_bytes[0:4])[0]
    if magic != 0x46546C67:
        return {"valid": False, "error": f"Invalid magic: 0x{magic:08X}"}
    version = struct.unpack('<I', glb_bytes[4:8])[0]
    if version != 2:
        return {"valid": False, "error": f"Unsupported glTF version: {version}"}
    total_length = struct.unpack('<I', glb_bytes[8:12])[0]
    if total_length != len(glb_bytes):
        return {"valid": False, "error": f"Declared length {total_length} != actual {len(glb_bytes)}"}

    # Structural validation: parse JSON chunk and check mesh/accessor integrity
    errors = []
    if len(glb_bytes) >= 20:
        json_len = struct.unpack('<I', glb_bytes[12:16])[0]
        json_type = struct.unpack('<I', glb_bytes[16:20])[0]
        if json_type != 0x4E4F534A:
            errors.append("JSON chunk type not 0x4E4F534A")
        else:
            try:
                gltf = _json.loads(glb_bytes[20:20+json_len].rstrip(b' \x00').decode('utf-8'))
                accessors = gltf.get("accessors", [])
                meshes = gltf.get("meshes", [])
                if not meshes:
                    errors.append("No meshes")
                for mi, mesh in enumerate(meshes):
                    for prim in mesh.get("primitives", []):
                        attrs = prim.get("attributes", {})
                        pos_idx = attrs.get("POSITION")
                        nrm_idx = attrs.get("NORMAL")
                        if pos_idx is not None:
                            pos_count = accessors[pos_idx].get("count", 0) if pos_idx < len(accessors) else 0
                            if pos_count == 0:
                                errors.append(f"Mesh {mi}: POSITION accessor count 0")
                            if nrm_idx is not None:
                                nrm_count = accessors[nrm_idx].get("count", 0) if nrm_idx < len(accessors) else 0
                                if nrm_count != pos_count:
                                    errors.append(
                                        f"Mesh {mi}: NORMAL count {nrm_count} != POSITION count {pos_count}")
                        else:
                            errors.append(f"Mesh {mi}: missing POSITION attribute")
            except Exception as e:
                errors.append(f"JSON parse failed: {e}")

    result = {
        "valid": len(errors) == 0,
        "version": version,
        "total_bytes": total_length,
        "sha256": hashlib.sha256(glb_bytes).hexdigest(),
    }
    if errors:
        result["errors"] = errors
    return result
