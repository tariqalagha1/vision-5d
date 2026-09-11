"""
Vision 5D — Heuristic DWG Geometry Extractor
Extracts LINE-like geometry from DWG R2000 binary when no converter is available.
"""
import struct, re, hashlib
from uuid import uuid4
from packages.universal_ingestion import BaseImporter, CADFormat, UnifiedGeometry


class HeuristicDWGImporter(BaseImporter):
    """Extract architectural geometry from DWG binary using heuristic pattern matching."""
    format = CADFormat.DWG

    def import_file(self, data: bytes, filename: str = "", format_info=None) -> UnifiedGeometry:
        import time
        t0 = time.time()
        source_hash = hashlib.sha256(data).hexdigest()

        # Detect version
        version = "Unknown"
        ver_map = {b'AC1015': 'R2000', b'AC1018': 'R2004', b'AC1021': 'R2007',
                   b'AC1024': 'R2010', b'AC1027': 'R2013', b'AC1032': 'R2018'}
        for sig, ver in ver_map.items():
            if data[:6] == sig:
                version = ver
                break

        warnings = [f"DWG {version} parsed heuristically. Install LibreDWG or ODA for full fidelity."]

        # ── Extract LINE endpoints from binary ──
        # DWG stores LINE entities with two XYZ points (6 doubles = 48 bytes)
        # Look for consecutive double pairs in architectural range
        lines = []
        coords = self._extract_architectural_coords(data)

        # Heuristic: pair coordinate triples as LINE start/end points
        if len(coords) >= 2:
            for i in range(0, len(coords) - 1, 2):
                x1, y1, z1 = coords[i]
                x2, y2, z2 = coords[i + 1]
                # Filter: skip degenerate lines, keep reasonable wall lengths
                length = ((x2-x1)**2 + (y2-y1)**2) ** 0.5
                if 100 < length < 50000:  # 100mm–50m typical wall length
                    lines.append({
                        "id": uuid4().hex[:8],
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    })

        # ── Extract text labels ──
        text_strings = re.findall(b'[\x20-\x7e]{3,30}', data[:len(data)//3])
        labels = []
        seen = set()
        for s in text_strings:
            decoded = s.decode('ascii', errors='replace').strip('\x00')
            if decoded and len(decoded) >= 2 and decoded not in seen:
                # Filter AutoCAD internals
                if not any(x in decoded for x in ['AcDb', 'AutoCAD', 'ObjectDBX', '{']):
                    if not all(c in '0123456789.+-eE ' for c in decoded):  # Not pure numbers
                        seen.add(decoded)
                        labels.append({"text": decoded, "position": (0, 0)})

        # ── Compute bounds ──
        if lines:
            xs = [l["x1"] for l in lines] + [l["x2"] for l in lines]
            ys = [l["y1"] for l in lines] + [l["y2"] for l in lines]
            bounds = (min(xs), min(ys), max(xs), max(ys))
            # Normalize to origin
            for line in lines:
                line["x1"] -= bounds[0]
                line["y1"] -= bounds[1]
                line["x2"] -= bounds[0]
                line["y2"] -= bounds[1]
            bounds = (0, 0, bounds[2]-bounds[0], bounds[3]-bounds[1])
        else:
            bounds = (0, 0, 100000, 100000)
            warnings.append("No LINE geometry extracted. File may contain only blocks/3D objects.")

        # Convert to UnifiedGeometry wall format
        walls = []
        for line in lines[:2000]:  # Cap at 2000 walls
            walls.append({
                "id": line["id"],
                "points": [(line["x1"], line["y1"]), (line["x2"], line["y2"])],
                "thickness": 120.0,
                "is_exterior": False,
            })

        return UnifiedGeometry(
            source_format="dwg", source_filename=filename,
            source_hash=source_hash, units="mm",
            walls=walls, text_labels=labels,
            bounds=bounds,
            importer_used=f"HeuristicDWGImporter+{version}",
            import_duration_ms=(time.time() - t0) * 1000,
            import_warnings=warnings,
        )

    def _extract_architectural_coords(self, data: bytes) -> list:
        """Extract coordinate triples in architectural range (0-200m)."""
        coords = []
        for i in range(0, len(data) - 24, 8):
            try:
                x = struct.unpack('<d', data[i:i+8])[0]
                y = struct.unpack('<d', data[i+8:i+16])[0]
                z = struct.unpack('<d', data[i+16:i+24])[0]
                if 0 <= x <= 200000 and 0 <= y <= 200000 and -5000 <= z <= 50000:
                    coords.append((x, y, z))
            except:
                pass
        return coords
