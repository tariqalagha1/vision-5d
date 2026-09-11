"""
Vision 5D — CAD Viewer Routes
Parse DWG/DXF (2D vector geometry) and serve 3D model files (STL/GLB/OBJ)
for the in-app CAD viewer.

These endpoints are stateless file->geometry utilities (no DB writes), so they
do NOT require an auth session — the CAD viewer must be usable instantly when a
file is dropped into the pipeline. Serving is limited to a dedicated data/cad/
directory.
"""
import os, math, hashlib, tempfile, shutil
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from packages.domain.database import get_db

logger = __import__("structlog").get_logger()

router = APIRouter(prefix="/api/v1/cad", tags=["CAD Viewer"])

# Dedicated storage for uploaded 3D model files
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAD_STORAGE_DIR = os.path.join(_ROOT, "data", "cad")
os.makedirs(CAD_STORAGE_DIR, exist_ok=True)

# 3D formats the browser renders with three.js
MESH_EXTENSIONS = {".stl", ".glb", ".gltf", ".obj", ".3ds"}
MAX_ENTITIES = 20000  # cap returned entities so huge drawings stay responsive


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _num(v, nd=3):
    """Round a float defensively (guards NaN/inf)."""
    try:
        f = float(v)
        if not math.isfinite(f):
            return 0.0
        return round(f, nd)
    except (TypeError, ValueError):
        return 0.0


def _serialize_entity(e) -> dict:
    """Convert a CADEntity dataclass into a JSON-safe dict."""
    pts = []
    for p in (e.points or []):
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            pts.append([_num(p[0]), _num(p[1])])
    return {
        "type": e.entity_type,
        "layer": e.layer or "0",
        "color": int(getattr(e, "color", 7) or 7),
        "points": pts,
        "radius": _num(getattr(e, "radius", 0.0)),
        "text": getattr(e, "text", "") or "",
        "rotation": _num(getattr(e, "rotation", 0.0), 5),
        "closed": bool(getattr(e, "closed", False)),
        "props": dict(getattr(e, "properties", None) or {}),
    }


def _parse_dxf_text(dxf_text: str, source_format: str, filename: str) -> dict:
    """Parse raw DXF text into renderable entities via DXFParser."""
    from packages.cad_import.dxf_parser import DXFParser

    parser = DXFParser()
    drawing = parser.parse(dxf_text)

    entities = []
    for e in drawing.entities:
        entities.append(_serialize_entity(e))
        if len(entities) >= MAX_ENTITIES:
            break

    b = drawing.bounds or (0, 0, 0, 0)
    return {
        "mode": "2d",
        "source_format": source_format,
        "filename": filename,
        "units": getattr(drawing, "units", "mm") or "mm",
        "bounds": {
            "min_x": _num(b[0]), "min_y": _num(b[1]),
            "max_x": _num(b[2]), "max_y": _num(b[3]),
        },
        "layers": sorted(drawing.layers) if drawing.layers else ["0"],
        "entities": entities,
        "entity_count": len(drawing.entities),
        "returned_count": len(entities),
        "truncated": len(drawing.entities) > MAX_ENTITIES,
        "warnings": [],
    }


def _dwg_to_dxf_text(contents: bytes, filename: str) -> Optional[str]:
    """Convert DWG bytes to DXF text using LibreDWG; returns None on failure."""
    from packages.universal_ingestion.dwg_production import DWGToDXFConverter

    tmpdir = tempfile.mkdtemp(prefix="v5d_cad_")
    dwg_path = os.path.join(tmpdir, filename or "input.dwg")
    with open(dwg_path, "wb") as f:
        f.write(contents)

    try:
        converter = DWGToDXFConverter()
        dxf_path, conv_info, err = converter.convert(dwg_path, tmpdir)
        if dxf_path and os.path.exists(dxf_path) and os.path.getsize(dxf_path) > 100:
            with open(dxf_path, "r", errors="ignore") as f:
                return f.read()
        return None
    except Exception as e:
        logger.error("dwg_to_dxf_failed", error=str(e))
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _dwg_heuristic_entities(contents: bytes, filename: str) -> dict:
    """Fallback: heuristic DWG import -> LINE entities (reduced fidelity)."""
    from packages.universal_ingestion.dwg_heuristic import HeuristicDWGImporter

    geo = HeuristicDWGImporter().import_file(contents, filename)
    entities = []
    for w in geo.walls[:MAX_ENTITIES]:
        pts = w.get("points") or []
        entities.append({
            "type": "LINE", "layer": "wall", "color": 7,
            "points": [[_num(p[0]), _num(p[1])] for p in pts if len(p) >= 2],
            "radius": 0, "text": "", "rotation": 0, "closed": False, "props": {},
        })
    b = geo.bounds or (0, 0, 0, 0)
    return {
        "mode": "2d",
        "source_format": "dwg",
        "filename": filename,
        "units": "mm",
        "bounds": {"min_x": _num(b[0]), "min_y": _num(b[1]),
                   "max_x": _num(b[2]), "max_y": _num(b[3])},
        "layers": ["wall"],
        "entities": entities,
        "entity_count": len(entities),
        "returned_count": len(entities),
        "truncated": False,
        "warnings": ["REDUCED FIDELITY: DWG parsed heuristically (LibreDWG conversion unavailable)."],
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("/parse")
async def cad_parse(file: UploadFile = File(...)):
    """Parse an uploaded CAD file and return renderable geometry.

    2D (DXF/DWG) -> {mode:'2d', entities:[...], layers:[...], bounds:{...}}
    3D (STL/GLB/OBJ) -> {mode:'3d', download_url:'/api/v1/cad/file?key=...'}
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file.")
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()

    # ── 2D: DXF ──
    if ext == ".dxf":
        dxf_text = contents.decode("ascii", errors="ignore")
        result = _parse_dxf_text(dxf_text, "dxf", filename)
        result["source_hash"] = hashlib.sha256(contents).hexdigest()
        return result

    # ── 2D: DWG (convert -> DXF, fallback heuristic) ──
    if ext == ".dwg":
        dxf_text = _dwg_to_dxf_text(contents, filename)
        if dxf_text:
            result = _parse_dxf_text(dxf_text, "dwg", filename)
        else:
            result = _dwg_heuristic_entities(contents, filename)
        result["source_hash"] = hashlib.sha256(contents).hexdigest()
        return result

    # ── 3D mesh formats ──
    if ext in MESH_EXTENSIONS:
        token = hashlib.sha256(contents).hexdigest()[:16] + ext
        dest = os.path.join(CAD_STORAGE_DIR, token)
        with open(dest, "wb") as f:
            f.write(contents)
        return {
            "mode": "3d",
            "source_format": ext.lstrip("."),
            "filename": filename,
            "download_url": f"/api/v1/cad/file?key={token}",
            "size_bytes": len(contents),
            "warnings": [],
        }

    raise HTTPException(400, f"Unsupported CAD format '.{ext or '?'}'. "
                              "Use DXF, DWG, STL, GLB/GLTF, OBJ, or 3DS.")


@router.get("/file")
async def cad_file(key: str):
    """Serve a stored 3D model file by its generated token."""
    safe = os.path.basename(key)
    if not safe or safe != key:
        raise HTTPException(400, "Invalid key.")
    path = os.path.join(CAD_STORAGE_DIR, safe)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found.")
    return FileResponse(path, filename=safe)


@router.get("/formats")
async def cad_formats():
    """List supported CAD formats and their rendering mode."""
    return {
        "formats": [
            {"ext": ".dxf", "mode": "2d", "label": "AutoCAD DXF (2D vector)"},
            {"ext": ".dwg", "mode": "2d", "label": "AutoCAD DWG (2D vector)"},
            {"ext": ".stl", "mode": "3d", "label": "STL mesh"},
            {"ext": ".glb", "mode": "3d", "label": "glTF Binary"},
            {"ext": ".gltf", "mode": "3d", "label": "glTF JSON"},
            {"ext": ".obj", "mode": "3d", "label": "Wavefront OBJ"},
            {"ext": ".3ds", "mode": "3d", "label": "3D Studio"},
        ]
    }
