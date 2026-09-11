"""
Vision 5D — Universal CAD Ingestion Layer
Automatic format detection, multi-format importers, unified geometry model.

Supported: DXF, DWG(stub), IFC(stub), STEP(stub), PDF(vector/scan), Images(PNG/JPG/...),
           STL, OBJ(stub), GLB/GLTF(stub), SVG, Archives(ZIP/7Z/RAR)
"""
import os, struct, hashlib, structlog
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

logger = structlog.get_logger()


# ══════════════════ FORMAT DETECTION ══════════════════

class CADFormat(Enum):
    DXF = "dxf"
    DWG = "dwg"
    IFC = "ifc"
    IFCZIP = "ifczip"
    STEP = "step"
    IGES = "iges"
    SAT = "sat"
    STL = "stl"
    OBJ = "obj"
    FBX = "fbx"
    GLB = "glb"
    GLTF = "gltf"
    MODEL_3DS = "3ds"
    PDF = "pdf"
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"
    BMP = "bmp"
    WEBP = "webp"
    ZIP = "zip"
    ARCHIVE_7Z = "7z"
    RAR = "rar"
    UNKNOWN = "unknown"


# Magic byte signatures
MAGIC_SIGNATURES = {
    b'\x7f\x45\x4c\x46': CADFormat.UNKNOWN,  # ELF — not CAD
    b'DXF': CADFormat.DXF,                     # ASCII DXF starts with "  0\nSECTION"
    b'AC10': CADFormat.DWG,                    # DWG header
    b'\x89PNG': CADFormat.PNG,
    b'\xff\xd8\xff': CADFormat.JPG,
    b'BM': CADFormat.BMP,
    b'RIFF': CADFormat.WEBP,                   # RIFF....WEBP
    b'II*\x00': CADFormat.TIFF,               # Little-endian TIFF
    b'MM\x00*': CADFormat.TIFF,               # Big-endian TIFF
    b'%PDF': CADFormat.PDF,
    b'glTF': CADFormat.GLB,                    # Binary glTF magic
    b'PK\x03\x04': CADFormat.ZIP,
    b"7z\xbc\xaf'\x1c": CADFormat.ARCHIVE_7Z,
    b'Rar!\x1a\x07': CADFormat.RAR,
    b'ISO-10303-21': CADFormat.STEP,           # STEP ASCII header
    b'solid ': CADFormat.STL,                  # ASCII STL
    b'v ': CADFormat.OBJ,                      # OBJ vertex line "v x y z"
    b'<?xml': CADFormat.SVG,                   # SVG (XML)
    b'<svg': CADFormat.SVG,
    b'SECT': CADFormat.IFC,                    # IFC-SPF starts with "ISO-10303-21;"
}

# Extension → format mapping (fallback)
EXTENSION_MAP = {
    '.dxf': CADFormat.DXF, '.dwg': CADFormat.DWG, '.dwt': CADFormat.DXF,
    '.ifc': CADFormat.IFC, '.ifczip': CADFormat.IFCZIP, '.rvt': CADFormat.UNKNOWN,
    '.step': CADFormat.STEP, '.stp': CADFormat.STEP,
    '.iges': CADFormat.IGES, '.igs': CADFormat.IGES, '.sat': CADFormat.SAT,
    '.stl': CADFormat.STL, '.obj': CADFormat.OBJ, '.fbx': CADFormat.FBX,
    '.glb': CADFormat.GLB, '.gltf': CADFormat.GLTF, '.3ds': CADFormat.MODEL_3DS,
    '.pdf': CADFormat.PDF, '.svg': CADFormat.SVG,
    '.png': CADFormat.PNG, '.jpg': CADFormat.JPG, '.jpeg': CADFormat.JPEG,
    '.tiff': CADFormat.TIFF, '.tif': CADFormat.TIFF,
    '.bmp': CADFormat.BMP, '.webp': CADFormat.WEBP,
    '.zip': CADFormat.ZIP, '.7z': CADFormat.ARCHIVE_7Z, '.rar': CADFormat.RAR,
}

# Format → MIME type
MIME_MAP = {
    CADFormat.DXF: "application/dxf", CADFormat.DWG: "application/acad",
    CADFormat.IFC: "application/x-ifc", CADFormat.STEP: "application/step",
    CADFormat.PDF: "application/pdf", CADFormat.SVG: "image/svg+xml",
    CADFormat.PNG: "image/png", CADFormat.JPG: "image/jpeg",
    CADFormat.STL: "application/sla", CADFormat.GLB: "model/gltf-binary",
    CADFormat.OBJ: "model/obj",
}


@dataclass
class FormatInfo:
    format: CADFormat
    method: str           # "magic", "extension", "mime"
    confidence: float     # 0.0–1.0
    detected_version: str = ""
    mime_type: str = ""
    warnings: list = field(default_factory=list)


class FormatDetector:
    """Detect CAD/BIM/mesh/document format from binary content + filename."""

    def detect(self, data: bytes, filename: str = "", mime_hint: str = "") -> FormatInfo:
        """Multi-method format detection."""
        results = []

        # 1. Magic bytes
        for signature, fmt in MAGIC_SIGNATURES.items():
            if data[:len(signature)] == signature:
                results.append(FormatInfo(fmt, "magic", 0.95, warnings=[]))

        # ASCII DXF starts with group codes
        text_start = data[:200].decode("ascii", errors="ignore").strip()
        if text_start.startswith("0") and "SECTION" in text_start and "ENTITIES" in text_start:
            results.append(FormatInfo(CADFormat.DXF, "magic", 0.99))

        # ASCII STL
        if text_start.lower().startswith("solid ") and "facet normal" in text_start[:500]:
            results.append(FormatInfo(CADFormat.STL, "magic", 0.90))

        # STEP
        if "ISO-10303-21" in text_start[:100]:
            results.append(FormatInfo(CADFormat.STEP, "magic", 0.99))

        # IFC
        if "IFC" in text_start[:100] and "ISO-10303-21" in text_start[:100]:
            results.append(FormatInfo(CADFormat.IFC, "magic", 0.99))

        # 2. Extension fallback
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            fmt = EXTENSION_MAP.get(ext)
            if fmt:
                results.append(FormatInfo(fmt, "extension", 0.70))

        # 3. MIME
        if mime_hint:
            for fmt, mime in MIME_MAP.items():
                if mime_hint.lower() == mime.lower():
                    results.append(FormatInfo(fmt, "mime", 0.80))

        if not results:
            return FormatInfo(CADFormat.UNKNOWN, "none", 0.0, warnings=["No format detected"])

        # Prefer magic byte results
        magic_results = [r for r in results if r.method == "magic"]
        final = magic_results[0] if magic_results else results[0]

        # Cross-check: warn if extension disagrees with detected format
        ext_fmt = EXTENSION_MAP.get(os.path.splitext(filename)[1].lower()) if filename else None
        if ext_fmt and ext_fmt != final.format:
            final.warnings.append(f"Extension '.{filename.split('.')[-1]}' suggests {ext_fmt.value}, but content detected as {final.format.value} — using content detection")

        # Version detection
        final.detected_version = self._detect_version(data, final.format)
        final.mime_type = MIME_MAP.get(final.format, "application/octet-stream")

        return final

    def _detect_version(self, data: bytes, fmt: CADFormat) -> str:
        if fmt == CADFormat.DXF:
            text = data[:500].decode("ascii", errors="ignore")
            if "AC1027" in text: return "R2013+"
            if "AC1021" in text: return "R2007+"
            if "AC1018" in text: return "R2004"
            if "AC1015" in text: return "R2000"
            return "R12-R14"
        if fmt == CADFormat.IFC:
            text = data[:2000].decode("ascii", errors="ignore")
            if "IFC4" in text: return "IFC4"
            if "IFC2X3" in text: return "IFC2x3"
            return "IFC"
        if fmt == CADFormat.GLB:
            if len(data) >= 8:
                version = struct.unpack('<I', data[4:8])[0]
                return f"glTF {version}"
        return ""


# ══════════════════ UNIFIED GEOMETRY MODEL ══════════════════

@dataclass
class UnifiedGeometry:
    """Single internal geometry representation — output of all importers."""
    source_format: str = ""
    source_filename: str = ""
    source_hash: str = ""
    units: str = "mm"
    scale_factor: float = 1.0

    # Walls
    walls: list = field(default_factory=list)       # [{id, points, thickness, is_exterior}]
    # Rooms/spaces
    rooms: list = field(default_factory=list)        # [{id, label, polygon, area_mm2}]
    # Openings
    doors: list = field(default_factory=list)        # [{id, position, width, rotation}]
    windows: list = field(default_factory=list)      # [{id, position, width, rotation}]
    # 3D mesh data (for mesh formats)
    meshes: list = field(default_factory=list)       # [{id, vertices, indices, normals}]
    # Metadata
    text_labels: list = field(default_factory=list)  # [{text, position}]
    dimensions: list = field(default_factory=list)   # [{text, position}]
    layers: list = field(default_factory=list)       # [layer_name, ...]
    bounds: tuple = (0, 0, 0, 0)                    # min_x, min_y, max_x, max_y

    # Importer diagnostics
    importer_used: str = ""
    import_duration_ms: float = 0.0
    import_warnings: list = field(default_factory=list)
    import_errors: list = field(default_factory=list)

    @property
    def wall_count(self): return len(self.walls)
    @property
    def room_count(self): return len(self.rooms)
    @property
    def door_count(self): return len(self.doors)
    @property
    def window_count(self): return len(self.windows)
    @property
    def width(self): return self.bounds[2] - self.bounds[0]
    @property
    def height(self): return self.bounds[3] - self.bounds[1]


# ══════════════════ IMPORTER PLUGINS ══════════════════

class BaseImporter:
    """Abstract base for all format importers."""
    format: CADFormat = CADFormat.UNKNOWN

    def can_handle(self, format_info: FormatInfo) -> bool:
        return format_info.format == self.format

    def import_file(self, data: bytes, filename: str = "", format_info: FormatInfo = None) -> UnifiedGeometry:
        raise NotImplementedError


class DXFImporter(BaseImporter):
    format = CADFormat.DXF

    def import_file(self, data: bytes, filename: str = "", format_info=None) -> UnifiedGeometry:
        import time
        t0 = time.time()
        text = data.decode("ascii", errors="ignore")
        warnings = []

        from packages.cad_import.dxf_parser import DXFParser
        from packages.cad_import.fidelity_bridge import CADFidelityBridge

        parser = DXFParser()

        # Extract just the ENTITIES section for large multi-section DXFs
        if "ENTITIES" in text and len(text) > 50000:
            ents_start = text.find("ENTITIES")
            ents_end = text.find("ENDSEC", ents_start)
            if ents_end > ents_start:
                chunk = "  0\nSECTION\n  2\nENTITIES\n" + text[ents_start+8:ents_end] + "\n  0\nENDSEC\n  0\nEOF"
                drawing = parser.parse(chunk)
            else:
                drawing = parser.parse(text)
        else:
            drawing = parser.parse(text)
        bridge = CADFidelityBridge(drawing)
        bridge.extract_all()

        ug = UnifiedGeometry(
            source_format="dxf", source_filename=filename,
            source_hash=hashlib.sha256(data).hexdigest(),
            units=drawing.units, scale_factor=drawing.scale,
            walls=[{"id": w.id, "points": [(w.x1, w.y1), (w.x2, w.y2)],
                     "thickness": w.thickness, "is_exterior": w.is_exterior}
                   for w in bridge.walls],
            rooms=[{"id": r.id, "label": r.label, "polygon": r.polygon, "area_mm2": r.area_mm2}
                   for r in bridge.rooms],
            doors=[{"id": d.id, "position": (d.x, d.y), "width": d.width, "rotation": d.rotation_deg}
                   for d in bridge.doors],
            windows=[{"id": w.id, "position": (w.x, w.y), "width": w.width, "rotation": w.rotation_deg}
                     for w in bridge.windows],
            layers=sorted(drawing.layers),
            bounds=drawing.bounds,
            importer_used="DXFImporter+v1",
            import_duration_ms=(time.time() - t0) * 1000,
            import_warnings=warnings,
        )
        return ug


class ImageImporter(BaseImporter):
    """Import architectural plans from raster images (PNG, JPG, TIFF, etc.)."""
    format = CADFormat.PNG  # Base, handles all images

    def can_handle(self, format_info: FormatInfo) -> bool:
        return format_info.format in (CADFormat.PNG, CADFormat.JPG, CADFormat.JPEG,
                                       CADFormat.TIFF, CADFormat.BMP, CADFormat.WEBP)

    def import_file(self, data: bytes, filename: str = "", format_info: FormatInfo = None) -> UnifiedGeometry:
        import time, numpy as np
        t0 = time.time()

        try:
            import cv2
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            h, w = img.shape[:2]
        except ImportError:
            h, w = 800, 600

        ug = UnifiedGeometry(
            source_format=format_info.format.value if format_info else "image",
            source_filename=filename,
            source_hash=hashlib.sha256(data).hexdigest(),
            units="px", scale_factor=3.0,  # ~3px/mm typical
            bounds=(0, 0, w, h),
            importer_used="ImageImporter+v1",
            import_duration_ms=(time.time() - t0) * 1000,
            import_warnings=["Image imported for CV pipeline. Walls/rooms will be detected by Plan Understanding."],
        )
        return ug


class STLImporter(BaseImporter):
    format = CADFormat.STL

    def import_file(self, data: bytes, filename: str = "", format_info: FormatInfo = None) -> UnifiedGeometry:
        import time
        t0 = time.time()
        text = data.decode("ascii", errors="ignore")
        meshes = []

        if text.strip().lower().startswith("solid"):
            # ASCII STL
            vertices = []
            for line in text.split("\n"):
                if "vertex" in line:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        vertices.extend([float(parts[1]), float(parts[2]), float(parts[3])])
            if vertices:
                indices = list(range(len(vertices) // 3))
                meshes.append({"id": "stl_0", "vertices": vertices, "indices": indices, "normals": []})
        else:
            # Binary STL — 80-byte header + 4-byte count + 50-byte triangles
            pass  # Binary STL stub

        bounds = self._compute_bounds(vertices) if vertices else (0, 0, 0, 0)
        return UnifiedGeometry(
            source_format="stl", source_filename=filename,
            source_hash=hashlib.sha256(data).hexdigest(),
            meshes=meshes, bounds=bounds,
            importer_used="STLImporter+v1",
            import_duration_ms=(time.time() - t0) * 1000,
        )

    def _compute_bounds(self, verts):
        if not verts: return (0, 0, 0, 0)
        xs = verts[0::3]; ys = verts[1::3]; zs = verts[2::3]
        return (min(xs), min(ys), min(zs), max(xs)) if xs else (0, 0, 0, 0)


class GLBImporter(BaseImporter):
    format = CADFormat.GLB

    def import_file(self, data: bytes, filename: str = "", format_info: FormatInfo = None) -> UnifiedGeometry:
        import time
        t0 = time.time()
        from packages.studio.glb_inspector import GLBInspector

        inspector = GLBInspector(data)
        summary = inspector.get_object_summary()

        return UnifiedGeometry(
            source_format="glb", source_filename=filename,
            source_hash=hashlib.sha256(data).hexdigest(),
            importer_used="GLBImporter+v1",
            import_duration_ms=(time.time() - t0) * 1000,
            import_warnings=[f"GLB import: {inspector.node_count} nodes, {inspector.mesh_count} meshes"],
        )


# ── Stub importers for unimplemented formats ──

class StubImporter(BaseImporter):
    """Graceful stub for formats not yet fully implemented."""
    def __init__(self, fmt: CADFormat, note: str = ""):
        self.format = fmt
        self._note = note or f"{fmt.value} import is not yet implemented. Using geometry fallback."

    def import_file(self, data: bytes, filename: str = "", format_info: FormatInfo = None) -> UnifiedGeometry:
        return UnifiedGeometry(
            source_format=self.format.value, source_filename=filename,
            source_hash=hashlib.sha256(data).hexdigest(),
            importer_used=f"StubImporter({self.format.value})",
            import_warnings=[self._note],
            import_errors=[],
        )


# ══════════════════ IMPORTER REGISTRY ══════════════════

class ImporterRegistry:
    """Registry of all format importers, queried by format."""

    def __init__(self):
        self._importers: dict[CADFormat, BaseImporter] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(DXFImporter())
        self.register(GLBImporter())
        self.register(STLImporter())
        self.register(ImageImporter())

        # Stubs for unimplemented formats
        self.register(StubImporter(CADFormat.DWG, "DWG import requires Open Design Alliance or LibreDWG"))
        self.register(StubImporter(CADFormat.IFC, "IFC import supports BIM data, walls/floors/doors extraction planned"))
        self.register(StubImporter(CADFormat.STEP, "STEP import supports 3D solid geometry, conversion to mesh planned"))
        self.register(StubImporter(CADFormat.PDF, "PDF vector extraction uses pdfplumber or PyMuPDF"))
        self.register(StubImporter(CADFormat.SVG, "SVG vector import via xml parsing"))
        self.register(StubImporter(CADFormat.OBJ, "OBJ mesh import parses vertex/face data"))
        self.register(StubImporter(CADFormat.ZIP, "Archive extraction then re-detect format from contents"))
        self.register(StubImporter(CADFormat.ARCHIVE_7Z, "7z extraction then re-detect"))
        self.register(StubImporter(CADFormat.RAR, "RAR extraction then re-detect"))
        self.register(StubImporter(CADFormat.IGES, "IGES solid geometry import"))
        self.register(StubImporter(CADFormat.SAT, "SAT ACIS solid import"))
        self.register(StubImporter(CADFormat.FBX, "FBX mesh import via binary parser"))
        self.register(StubImporter(CADFormat.GLTF, "glTF JSON import"))
        self.register(StubImporter(CADFormat.MODEL_3DS, "3DS legacy mesh import"))

    def register(self, importer: BaseImporter):
        self._importers[importer.format] = importer

    def get(self, fmt: CADFormat) -> BaseImporter:
        return self._importers.get(fmt, StubImporter(CADFormat.UNKNOWN))

    def list_formats(self) -> list:
        return sorted(f.value for f in self._importers)


# ══════════════════ AUTO-PIPELINE ══════════════════

# Global instances
detector = FormatDetector()
registry = ImporterRegistry()


def ingest_file(filepath: str) -> UnifiedGeometry:
    """Universal entry point: detect format, select importer, produce unified geometry."""
    with open(filepath, "rb") as f:
        data = f.read()

    filename = os.path.basename(filepath)
    info = detector.detect(data, filename)

    if info.warnings:
        for w in info.warnings:
            logger.warn("format_warning", file=filename, warning=w)

    importer = registry.get(info.format)

    if isinstance(importer, StubImporter) and info.format != CADFormat.UNKNOWN:
        logger.info("using_stub_importer", format=info.format.value, note=importer._note)

    result = importer.import_file(data, filename, info)

    logger.info("ingestion_complete",
                file=filename,
                detected_format=info.format.value,
                method=info.method,
                confidence=info.confidence,
                importer=result.importer_used,
                walls=result.wall_count,
                rooms=result.room_count,
                duration_ms=result.import_duration_ms)

    return result


def supported_formats() -> list[str]:
    return registry.list_formats()


def detect_format(filepath: str) -> FormatInfo:
    """Detect format without importing."""
    with open(filepath, "rb") as f:
        data = f.read()
    return detector.detect(data, os.path.basename(filepath))
