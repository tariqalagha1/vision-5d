"""
Vision 5D — Independent GLB Inspector
Parses GLB/glTF 2.0 files without using the exporter.
Extracts: nodes, meshes, materials, transforms, colors, furniture objects.
Used for certification: verifies exported Studio GLB fidelity.
"""
import struct, json as _json, hashlib
from typing import Optional


class GLBInspector:
    """Load and inspect a GLB binary file independently of the exporter."""

    def __init__(self, glb_bytes: bytes):
        self.raw = glb_bytes
        self._gltf = None
        self._binary_buffer = b''
        self._valid = False
        self._errors = []
        self._parse()

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def errors(self) -> list[str]:
        return self._errors

    @property
    def gltf(self) -> dict:
        return self._gltf or {}

    @property
    def version(self) -> int:
        if not self._valid: return 0
        return struct.unpack('<I', self.raw[4:8])[0]

    @property
    def node_count(self) -> int:
        return len(self._gltf.get('nodes', []))

    @property
    def mesh_count(self) -> int:
        return len(self._gltf.get('meshes', []))

    @property
    def material_count(self) -> int:
        return len(self._gltf.get('materials', []))

    # ── Parsing ──

    def _parse(self):
        if len(self.raw) < 12:
            self._errors.append("File too short (< 12 bytes)")
            return
        magic = struct.unpack('<I', self.raw[0:4])[0]
        if magic != 0x46546C67:
            self._errors.append(f"Invalid magic: 0x{magic:08X}")
            return
        self._valid = True

        total_len = struct.unpack('<I', self.raw[8:12])[0]
        pos = 12
        while pos < total_len and pos + 8 <= len(self.raw):
            chunk_len = struct.unpack('<I', self.raw[pos:pos+4])[0]
            chunk_type = struct.unpack('<I', self.raw[pos+4:pos+8])[0]
            pos += 8
            if pos + chunk_len > len(self.raw):
                break
            chunk_data = self.raw[pos:pos+chunk_len]
            pos += chunk_len

            if chunk_type == 0x4E4F534A:  # JSON
                self._gltf = _json.loads(chunk_data.decode('utf-8'))
            elif chunk_type == 0x004E4942:  # BIN
                self._binary_buffer = chunk_data

    # ── Inspection ──

    def get_material_color(self, mat_idx: int) -> Optional[str]:
        """Get the base color of a material as a hex string."""
        mats = self._gltf.get('materials', [])
        if mat_idx < 0 or mat_idx >= len(mats):
            return None
        pbr = mats[mat_idx].get('pbrMetallicRoughness', {})
        factor = pbr.get('baseColorFactor', [1, 1, 1, 1])
        r, g, b = int(factor[0]*255), int(factor[1]*255), int(factor[2]*255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_material_roughness(self, mat_idx: int) -> float:
        mats = self._gltf.get('materials', [])
        if mat_idx < 0 or mat_idx >= len(mats):
            return 0.7
        return mats[mat_idx].get('pbrMetallicRoughness', {}).get('roughnessFactor', 0.7)

    def get_node_transform(self, node_idx: int) -> dict:
        """Get position, rotation (quaternion→euler), scale for a node."""
        nodes = self._gltf.get('nodes', [])
        if node_idx < 0 or node_idx >= len(nodes):
            return {}
        node = nodes[node_idx]
        pos = node.get('translation', [0, 0, 0]) if 'translation' in node else list(node.get('matrix', [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,1]))[12:15] if 'matrix' in node else [0, 0, 0]
        rot = node.get('rotation', [0, 0, 0, 1])  # quaternion
        scl = node.get('scale', [1, 1, 1])
        # Quaternion to approximate euler Y
        euler_y = _quat_to_euler_y(rot)
        return {
            'position': pos,
            'rotation_y_deg': round(euler_y, 1),
            'scale': scl,
            'name': node.get('name', ''),
        }

    def get_node_by_name(self, name_pattern: str) -> list[dict]:
        """Find all nodes whose name contains the pattern."""
        nodes = self._gltf.get('nodes', [])
        results = []
        for i, node in enumerate(nodes):
            if name_pattern.lower() in (node.get('name', '') or '').lower():
                transform = self.get_node_transform(i)
                mesh_idx = node.get('mesh')
                mat_idx = None
                if mesh_idx is not None:
                    mesh = self._gltf.get('meshes', [])[mesh_idx]
                    prim = mesh.get('primitives', [{}])[0]
                    mat_idx = prim.get('material')
                results.append({
                    'index': i,
                    'name': node.get('name', ''),
                    'position': transform.get('position'),
                    'rotation_y_deg': transform.get('rotation_y_deg'),
                    'scale': transform.get('scale'),
                    'mesh_index': mesh_idx,
                    'material_index': mat_idx,
                    'material_color': self.get_material_color(mat_idx) if mat_idx is not None else None,
                })
        return results

    def get_object_summary(self) -> dict:
        """Return a summary of all objects in the GLB."""
        nodes = self._gltf.get('nodes', [])
        meshes = self._gltf.get('meshes', [])
        materials = self._gltf.get('materials', [])

        furniture_nodes = []
        arch_nodes = []
        for i, node in enumerate(nodes):
            name = node.get('name', '')
            info = self.get_node_by_name(name[:20])
            if info:
                info = info[0]
            else:
                info = self.get_node_transform(i)

            entry = {
                'name': name,
                'position': info.get('position'),
                'material_color': info.get('material_color'),
            }
            if 'furniture' in name.lower() or 'chair' in name.lower() or 'table' in name.lower() or 'sofa' in name.lower():
                furniture_nodes.append(entry)
            elif name:
                arch_nodes.append(entry)

        return {
            'total_nodes': len(nodes),
            'total_meshes': len(meshes),
            'total_materials': len(materials),
            'furniture_objects': furniture_nodes,
            'architectural_objects': arch_nodes,
            'materials_summary': [
                {'index': mi, 'color': self.get_material_color(mi),
                 'roughness': self.get_material_roughness(mi),
                 'name': m.get('name', '')}
                for mi, m in enumerate(materials)
            ],
        }

    def compare_to_snapshot(self, snapshot: dict) -> dict:
        """Compare GLB contents to a Studio version snapshot."""
        summary = self.get_object_summary()
        matches = []
        mismatches = []

        # Compare furniture count
        snap_furn = snapshot.get('draft_snapshot', {}).get('furniture_instances', [])
        found_furn = summary['furniture_objects']
        matches.append({
            'property': 'furniture_count',
            'studio_value': len(snap_furn),
            'exported_value': len(found_furn),
            'match': len(snap_furn) == len(found_furn),
        })

        # Compare finishes
        finishes = snapshot.get('draft_snapshot', {}).get('finishes', {})
        for mat in summary['materials_summary']:
            color = mat['color']
            name = mat.get('name', '').lower()
            if 'floor' in name and finishes.get('floor_color'):
                matches.append({
                    'property': 'floor_color',
                    'studio_value': finishes['floor_color'],
                    'exported_value': color,
                    'match': _colors_match(finishes['floor_color'], color),
                })
            if 'wall' in name and finishes.get('wall_color'):
                matches.append({
                    'property': 'wall_color',
                    'studio_value': finishes['wall_color'],
                    'exported_value': color,
                    'match': _colors_match(finishes['wall_color'], color),
                })

        # Compare furniture transforms
        for i, fi in enumerate(snap_furn):
            if i < len(found_furn):
                fn = found_furn[i]
                matches.append({
                    'property': f'furniture[{i}].position',
                    'studio_value': fi.get('position'),
                    'exported_value': fn.get('position'),
                    'match': _vec3_close(fi.get('position'), fn.get('position'), 100),
                })

        matches.extend(mismatches)
        all_match = all(m['match'] for m in matches)
        return {
            'all_match': all_match,
            'comparisons': matches,
            'studio_furniture_count': len(snap_furn),
            'exported_furniture_count': len(found_furn),
        }


def _quat_to_euler_y(q: list) -> float:
    """Convert quaternion [x,y,z,w] to approximate euler Y (degrees)."""
    import math
    if len(q) < 4:
        return 0
    siny = 2.0 * (q[3] * q[1] + q[0] * q[2])
    cosy = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    return math.degrees(math.atan2(siny, cosy))


def _colors_match(a: str, b: str) -> bool:
    """Compare two color hex strings with tolerance."""
    if not a or not b:
        return False
    a = a.lstrip('#')
    b = b.lstrip('#')
    if len(a) != 6 or len(b) != 6:
        return a == b
    try:
        ra, ga, ba = int(a[0:2],16), int(a[2:4],16), int(a[4:6],16)
        rb, gb, bb = int(b[0:2],16), int(b[2:4],16), int(b[4:6],16)
        return abs(ra-rb) <= 10 and abs(ga-gb) <= 10 and abs(ba-bb) <= 10
    except ValueError:
        return a == b


def _vec3_close(a, b, tolerance: float) -> bool:
    """Check if two 3D vectors are close within tolerance."""
    if not a or not b:
        return False
    try:
        return all(abs(float(a[i]) - float(b[i])) < tolerance for i in range(3))
    except (IndexError, ValueError, TypeError):
        return False


def inspect_glb_file(filepath: str) -> dict:
    """Load and inspect a GLB file from disk."""
    with open(filepath, 'rb') as f:
        data = f.read()
    inspector = GLBInspector(data)
    return {
        'valid': inspector.valid,
        'version': inspector.version,
        'node_count': inspector.node_count,
        'mesh_count': inspector.mesh_count,
        'material_count': inspector.material_count,
        'summary': inspector.get_object_summary(),
        'size_bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
    }
