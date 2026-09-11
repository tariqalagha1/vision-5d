"""
Vision 5D — Universal CAD/BIM Ingestion Engine
Plugin-based importer architecture. Auto-detects, validates, imports, normalizes.
All importers output HermesGeometryModel — downstream never sees source format.
"""
import os, sys, time, hashlib, struct, re
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4
from typing import Optional
import structlog

logger = structlog.get_logger()

# ══════════════════ UNIFIED GEOMETRY MODEL ══════════════════

class GeometryType(Enum):
    SOLID = "solid"
    SURFACE = "surface"
    MESH = "mesh"
    WIREFRAME = "wireframe"
    POINT_CLOUD = "point_cloud"
    BREP = "brep"
    ASSEMBLY = "assembly"

class UnitSystem(Enum):
    MM = "mm"
    CM = "cm"
    M = "m"
    INCH = "inch"
    FOOT = "ft"
    UNKNOWN = "unknown"

class CoordinateSystem(Enum):
    RIGHT_HANDED_Y_UP = "rh_y_up"
    RIGHT_HANDED_Z_UP = "rh_z_up"
    LEFT_HANDED_Z_UP = "lh_z_up"
    UNKNOWN = "unknown"


@dataclass
class HermesGeometryModel:
    """Single internal geometry representation — output of ALL importers."""
    source_format: str = ""
    source_filename: str = ""
    source_hash: str = ""
    source_version: str = ""
    units: str = "mm"
    coordinate_system: str = "rh_y_up"

    # Bodies and solids
    bodies: list = field(default_factory=list)
    solids: list = field(default_factory=list)

    # Mesh data
    meshes: list = field(default_factory=list)       # [{id, vertices, indices, normals, uvs, material}]
    vertices_total: int = 0
    triangles_total: int = 0

    # Faces, edges
    faces: list = field(default_factory=list)
    edges: list = field(default_factory=list)

    # Materials
    materials: list = field(default_factory=list)
    layers: list = field(default_factory=list)

    # Assembly hierarchy
    assemblies: list = field(default_factory=list)    # [{name, children, transform}]
    assembly_root: str = ""

    # Metadata
    metadata: dict = field(default_factory=dict)
    transforms: list = field(default_factory=list)

    # Bounds
    bounds_min: tuple = (0, 0, 0)
    bounds_max: tuple = (0, 0, 0)

    # Walls/rooms/openings (architectural)
    walls: list = field(default_factory=list)
    rooms: list = field(default_factory=list)
    doors: list = field(default_factory=list)
    windows: list = field(default_factory=list)

    @property
    def wall_count(self): return len(self.walls)
    @property
    def room_count(self): return len(self.rooms)
    @property
    def door_count(self): return len(self.doors)
    @property
    def window_count(self): return len(self.windows)
    @property
    def mesh_count(self): return len(self.meshes)
    @property
    def width(self): return self.bounds_max[0] - self.bounds_min[0]
    @property
    def height(self): return self.bounds_max[1] - self.bounds_min[1]
    @property
    def depth(self): return self.bounds_max[2] - self.bounds_min[2]


# ══════════════════ IMPORT RESULT ══════════════════

class ImportStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    UNSUPPORTED_VERSION = "unsupported_version"
    CORRUPTED = "corrupted"
    ENCRYPTED = "encrypted"
    UNSUPPORTED_FORMAT = "unsupported_format"
    CONVERTER_REQUIRED = "converter_required"
    LICENSE_REQUIRED = "license_required"


@dataclass
class ImportResult:
    status: ImportStatus = ImportStatus.SUCCESS
    geometry: Optional[HermesGeometryModel] = None
    importer_name: str = ""
    import_duration_ms: float = 0.0
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    diagnostic_message: str = ""
    recommended_action: str = ""
    detected_format: str = ""
    detected_version: str = ""
    file_size_bytes: int = 0

    @property
    def success(self): return self.status == ImportStatus.SUCCESS


# ══════════════════ IMPORTER INTERFACE ══════════════════

class ICADImporter(ABC):
    """Plugin-based importer interface. All importers implement this."""

    @abstractmethod
    def can_read(self, data: bytes, filename: str = "") -> bool:
        """Check if this importer can handle the given file."""
        ...

    @abstractmethod
    def import_file(self, data: bytes, filename: str = "",
                    format_info: dict = None) -> ImportResult:
        """Import the file and produce a HermesGeometryModel."""
        ...

    @abstractmethod
    def normalize(self, raw_data) -> HermesGeometryModel:
        """Normalize importer-specific data into HermesGeometryModel."""
        ...

    @property
    @abstractmethod
    def format_name(self) -> str: ...

    @property
    @abstractmethod
    def supported_versions(self) -> list[str]: ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]: ...

    @property
    def requires_converter(self) -> bool: return False

    @property
    def requires_license(self) -> bool: return False


# ══════════════════ STUB IMPORTER BASE ══════════════════

class StubImporter(ICADImporter):
    """Graceful stub with diagnostic messages for unsupported/not-yet-implemented formats."""

    def __init__(self, format_name: str, extensions: list[str],
                 versions: list[str] = None, notes: str = "",
                 requires_converter: bool = False, requires_license: bool = False):
        self._format_name = format_name
        self._extensions = extensions
        self._versions = versions or ["unknown"]
        self._notes = notes
        self._requires_converter = requires_converter
        self._requires_license = requires_license

    @property
    def format_name(self) -> str: return self._format_name
    @property
    def supported_versions(self) -> list[str]: return self._versions
    @property
    def supported_extensions(self) -> list[str]: return self._extensions
    @property
    def requires_converter(self) -> bool: return self._requires_converter
    @property
    def requires_license(self) -> bool: return self._requires_license

    def can_read(self, data: bytes, filename: str = "") -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self._extensions

    def import_file(self, data: bytes, filename: str = "",
                    format_info: dict = None) -> ImportResult:
        ext = os.path.splitext(filename)[1].lower()
        sha = hashlib.sha256(data).hexdigest()

        ver = self._detect_version(data) if hasattr(self, '_detect_version') else "unknown"

        # Determine status
        if self.requires_license:
            status = ImportStatus.LICENSE_REQUIRED
            msg = f"{self.format_name} import requires a licensed SDK."
            action = f"Purchase {self.format_name} SDK license or export to STEP."
        elif self.requires_converter:
            status = ImportStatus.CONVERTER_REQUIRED
            msg = f"{self.format_name} import requires an external converter."
            action = f"Install {self.format_name} converter or export to STEP/DXF."
        else:
            status = ImportStatus.PARTIAL
            msg = f"{self.format_name} importer not yet fully implemented."
            action = f"Export {self.format_name} file to STEP, IFC, or DXF for full support."

        return ImportResult(
            status=status,
            importer_name=f"{self.format_name}Importer (stub)",
            detected_format=ext.lstrip("."),
            detected_version=ver,
            file_size_bytes=len(data),
            diagnostic_message=msg,
            recommended_action=action,
            warnings=[msg],
        )

    def normalize(self, raw_data) -> HermesGeometryModel:
        return HermesGeometryModel(source_format=self.format_name.lower())


# ══════════════════ FORMAT DETECTOR ══════════════════

@dataclass
class FormatInfo:
    format: str
    version: str = ""
    encoding: str = ""
    units: str = "mm"
    coordinate_system: str = "rh_y_up"
    is_corrupted: bool = False
    magic_bytes: str = ""
    confidence: float = 0.0
    warnings: list = field(default_factory=list)


class UniversalFormatDetector:
    """Detect any CAD/BIM format from binary content."""

    SIGNATURES = {
        b'AC10': ('dwg', 0.95),
        b'\x89PNG': ('png', 0.99),
        b'\xff\xd8\xff': ('jpg', 0.99),
        b'%PDF': ('pdf', 0.99),
        b'glTF': ('glb', 0.99),
        b'PK\x03\x04': ('zip', 0.90),
        b"7z\xbc\xaf'\x1c": ('7z', 0.95),
        b'Rar!\x1a\x07': ('rar', 0.95),
        b'BM': ('bmp', 0.90),
        b'II*\x00': ('tiff', 0.95),
        b'MM\x00*': ('tiff', 0.95),
    }

    TEXT_SIGNATURES = {
        'ISO-10303-21;': ('step', 0.99),
        'HEADER;': ('step', 0.90),
        'FILE_DESCRIPTION': ('step', 0.90),
        'solid ': ('stl', 0.90),
        'facet normal': ('stl', 0.95),
        '<?xml': ('xml', 0.80),
        'IFC': ('ifc', 0.90),      # Must check further — IFC also starts with ISO-10303
        'SECT': ('dxf', 0.90),     # Actually "0\nSECTION\n2\nENTITIES"
    }

    @classmethod
    def detect(cls, data: bytes, filename: str = "") -> FormatInfo:
        """Multi-method format detection."""
        ext = os.path.splitext(filename)[1].lower()

        # 1. Magic bytes
        for sig, (fmt, conf) in cls.SIGNATURES.items():
            if data[:len(sig)] == sig:
                return FormatInfo(format=fmt, magic_bytes=sig.hex(),
                                 confidence=conf, version=cls._version_for(fmt, data))

        # 2. Text signatures (first 200 bytes)
        text_start = data[:200].decode('ascii', errors='ignore')
        for sig, (fmt, conf) in cls.TEXT_SIGNATURES.items():
            if sig in text_start:
                # Disambiguate IFC vs STEP
                if fmt == 'ifc' and 'IFC' in text_start[:100]:
                    return FormatInfo(format='ifc', confidence=0.95, version=cls._ifc_version(text_start))
                if fmt == 'step' and 'IFC' not in text_start[:100]:
                    return FormatInfo(format='step', confidence=0.95, version=cls._step_version(text_start))
                if fmt != 'step' and fmt != 'ifc':
                    return FormatInfo(format=fmt, confidence=conf)

        # ASCII DXF
        text_500 = data[:500].decode('ascii', errors='ignore')
        if 'ENTITIES' in text_500 and 'ENDSEC' in text_500:
            return FormatInfo(format='dxf', confidence=0.99, version=cls._dxf_version(text_500))

        # ASCII STL
        text_start_lower = text_start.lower()
        if text_start_lower.startswith('solid '):
            return FormatInfo(format='stl', confidence=0.90)

        # 3. Extension fallback
        ext_map = {
            '.dxf': 'dxf', '.dwg': 'dwg', '.dwf': 'dwf',
            '.step': 'step', '.stp': 'step',
            '.stl': 'stl',
            '.iges': 'iges', '.igs': 'iges',
            '.ifc': 'ifc',
            '.obj': 'obj', '.fbx': 'fbx',
            '.pdf': 'pdf',
            '.ipt': 'ipt', '.iam': 'iam',
            '.rvt': 'rvt',
            '.sldprt': 'sldprt', '.sldasm': 'sldasm',
            '.x_t': 'parasolid', '.x_b': 'parasolid',
            '.sat': 'sat',
            '.3dm': '3dm',
            '.catpart': 'catpart', '.catproduct': 'catproduct', '.cgr': 'cgr',
            '.prt': 'prt', '.asm': 'asm',
        }
        fmt = ext_map.get(ext, 'unknown')
        return FormatInfo(format=fmt, confidence=0.50 if fmt != 'unknown' else 0.0,
                         warnings=[f"Extension-based detection only ({ext}). Install format-specific importer."])

    @classmethod
    def _version_for(cls, fmt: str, data: bytes) -> str:
        if fmt == 'dwg':
            vm = {b'AC1015': 'R2000', b'AC1018': 'R2004', b'AC1021': 'R2007',
                  b'AC1024': 'R2010', b'AC1027': 'R2013', b'AC1032': 'R2018'}
            return vm.get(data[:6], 'unknown')
        if fmt == 'glb':
            if len(data) >= 8:
                v = struct.unpack('<I', data[4:8])[0]
                return f"glTF {v}"
        return ''

    @classmethod
    def _dxf_version(cls, text: str) -> str:
        for v, s in [('R2013+', 'AC1027'), ('R2007+', 'AC1021'), ('R2004', 'AC1018'), ('R2000', 'AC1015')]:
            if s in text: return v
        return 'R12-R14'

    @classmethod
    def _step_version(cls, text: str) -> str:
        if 'AP242' in text: return 'AP242'
        if 'AP214' in text: return 'AP214'
        if 'AP203' in text: return 'AP203'
        return 'AP203/214'

    @classmethod
    def _ifc_version(cls, text: str) -> str:
        if 'IFC4' in text: return 'IFC4'
        if 'IFC2X3' in text: return 'IFC2x3'
        return 'IFC'


# ══════════════════ IMPORT MANAGER ══════════════════

class ImportManager:
    """Auto-dispatches files to the correct importer. Plugin-based."""

    def __init__(self):
        self._importers: list[ICADImporter] = []
        self._register_all()

    def register(self, importer: ICADImporter):
        self._importers.append(importer)
        logger.info("importer_registered", format=importer.format_name,
                    extensions=importer.supported_extensions)

    def import_file(self, filepath: str) -> ImportResult:
        """Universal entry point: detect → dispatch → import → normalize."""
        t0 = time.time()

        if not os.path.exists(filepath):
            return ImportResult(status=ImportStatus.CORRUPTED, diagnostic_message=f"File not found: {filepath}")

        with open(filepath, 'rb') as f:
            data = f.read()

        filename = os.path.basename(filepath)
        info = UniversalFormatDetector.detect(data, filename)

        if info.warnings:
            for w in info.warnings:
                logger.warn("format_warning", file=filename, warning=w)

        # Try registered importers first
        for importer in self._importers:
            if importer.can_read(data, filename):
                result = importer.import_file(data, filename, {
                    "detected": info.format, "version": info.version,
                    "confidence": info.confidence,
                })
                result.detected_format = info.format
                result.detected_version = info.version
                result.file_size_bytes = len(data)
                result.import_duration_ms = (time.time() - t0) * 1000
                return result

        # No importer found
        ext = os.path.splitext(filename)[1].lower()
        return ImportResult(
            status=ImportStatus.UNSUPPORTED_FORMAT,
            importer_name="None",
            detected_format=info.format,
            detected_version=info.version,
            file_size_bytes=len(data),
            import_duration_ms=(time.time() - t0) * 1000,
            diagnostic_message=f"No importer available for .{ext} ({info.format}).",
            recommended_action=f"Export as STEP, IFC, DXF, or STL. Then re-upload.",
        )

    def supported_formats(self) -> dict:
        """Return all supported formats with their importers."""
        return {imp.format_name: {
            "extensions": imp.supported_extensions,
            "versions": imp.supported_versions,
            "requires_converter": imp.requires_converter,
            "requires_license": imp.requires_license,
        } for imp in self._importers}

    def _register_all(self):
        # ── Full importers (with adapter wrapper) ──
        from packages.universal_ingestion import DXFImporter, STLImporter, GLBImporter, ImageImporter

        class LegacyAdapter(ICADImporter):
            """Adapts existing BaseImporter classes to ICADImporter interface."""
            def __init__(self, instance, name, extensions, versions=None):
                self._inst = instance
                self._name = name
                self._exts = extensions
                self._vers = versions or ['all']
            @property
            def format_name(self): return self._name
            @property
            def supported_versions(self): return self._vers
            @property
            def supported_extensions(self): return self._exts
            def can_read(self, data, filename=''):
                ext = os.path.splitext(filename)[1].lower()
                return ext in self._exts
            def import_file(self, data, filename='', format_info=None):
                from packages.universal_ingestion import UnifiedGeometry
                t0 = time.time()
                result = self._inst.import_file(data, filename, format_info)
                geo = HermesGeometryModel(
                    source_format=self._name.lower(), source_filename=filename,
                    source_hash=hashlib.sha256(data).hexdigest(),
                    walls=result.walls if hasattr(result, 'walls') else [],
                    rooms=result.rooms if hasattr(result, 'rooms') else [],
                    doors=result.doors if hasattr(result, 'doors') else [],
                    windows=result.windows if hasattr(result, 'windows') else [],
                    meshes=result.meshes if hasattr(result, 'meshes') else [],
                    layers=result.layers if hasattr(result, 'layers') else [],
                )
                return ImportResult(status=ImportStatus.SUCCESS, geometry=geo,
                                   importer_name=f"{self._name}Importer",
                                   import_duration_ms=(time.time()-t0)*1000,
                                   file_size_bytes=len(data))
            def normalize(self, raw): return raw

        self.register(LegacyAdapter(DXFImporter(), "DXF", ['.dxf']))
        self.register(LegacyAdapter(STLImporter(), "STL", ['.stl']))
        self.register(LegacyAdapter(GLBImporter(), "GLB", ['.glb', '.gltf']))
        self.register(LegacyAdapter(ImageImporter(), "Image", ['.png','.jpg','.jpeg','.tiff','.bmp','.webp']))

        from packages.universal_ingestion.dwg_production import ProductionDWGImporter
        dwg = ProductionDWGImporter()
        self.register(LegacyAdapter(dwg, "DWG", ['.dwg'], ['R12','R13','R14','R2000','R2004','R2007','R2010','R2013','R2018']))

        # ── Stub importers with diagnostics ──
        self.register(StubImporter(
            "STEP", ['.step', '.stp'], ['AP203', 'AP214', 'AP242'],
            "ISO 10303-21 solid models. Install pythonOCC or FreeCAD for full import."
        ))
        self.register(StubImporter(
            "IGES", ['.iges', '.igs'], ['5.3'],
            "Initial Graphics Exchange Specification. Legacy format."
        ))
        self.register(StubImporter(
            "IFC", ['.ifc'], ['IFC2x3', 'IFC4', 'IFC4.3'],
            "Industry Foundation Classes. Full BIM data. Install IfcOpenShell for import."
        ))
        self.register(StubImporter(
            "SolidWorks", ['.sldprt', '.sldasm'], ['2018-2024'],
            "", requires_converter=True
        ))
        self.register(StubImporter(
            "Inventor", ['.ipt', '.iam'], ['2018-2024'],
            "", requires_converter=True
        ))
        self.register(StubImporter(
            "Revit", ['.rvt'], ['2018-2024'],
            "Autodesk Revit BIM models. Export to IFC or DWG for import.",
            requires_license=True
        ))
        self.register(StubImporter(
            "CATIA", ['.catpart', '.catproduct', '.cgr'], ['V5', 'V6', '3DEXPERIENCE'],
            "Dassault CATIA. Export to STEP or IGES.",
            requires_license=True
        ))
        self.register(StubImporter(
            "Creo", ['.prt', '.asm'], ['4.0-10.0'],
            "PTC Creo / Pro/ENGINEER. Export to STEP.",
            requires_license=True
        ))
        self.register(StubImporter(
            "Parasolid", ['.x_t', '.x_b'], [''],
            "Siemens Parasolid kernel format."
        ))
        self.register(StubImporter(
            "ACIS", ['.sat'], [''],
            "Spatial ACIS solid modeling kernel."
        ))
        self.register(StubImporter(
            "Rhino", ['.3dm'], ['5-8'],
            "Rhinoceros 3D. Export to STEP, IGES, or DXF."
        ))
        self.register(StubImporter(
            "FBX", ['.fbx'], [''],
            "Autodesk FBX interchange. Mesh + animation."
        ))
        self.register(StubImporter(
            "OBJ", ['.obj'], [''],
            "Wavefront OBJ. Mesh with materials."
        ))
        self.register(StubImporter(
            "PDF", ['.pdf'], [''],
            "Vector PDF extraction. Install PyMuPDF or pdfplumber."
        ))


# ══════════════════ GLOBAL INSTANCE ══════════════════

import_manager = ImportManager()
