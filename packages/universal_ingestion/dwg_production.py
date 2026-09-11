"""
Vision 5D — Production-Grade DWG Importer
Auto-detects DWG converters, auto-converts to DXF, full-fidelity import.
Falls back to heuristic when no converter is available.
"""
import os, sys, subprocess, shutil, tempfile, time, hashlib
import structlog
from dataclasses import dataclass, field
from uuid import uuid4

logger = structlog.get_logger()

# ══════════════════ CONVERTER DETECTION ══════════════════

@dataclass
class ConverterInfo:
    name: str
    path: str
    command: str         # How to invoke: "dwg2dxf {input} -o {output}"
    available: bool = False
    version: str = ""
    notes: str = ""


class DWGConverterDetector:
    """Detect installed DWG→DXF converters on the system."""

    def detect_all(self) -> list[ConverterInfo]:
        converters = []

        # 1. LibreDWG (dwg2dxf)
        libredwg = self._detect_libredwg()
        if libredwg:
            converters.append(libredwg)

        # 2. ODA File Converter (Windows)
        oda = self._detect_oda()
        if oda:
            converters.append(oda)

        # 3. ezdxf DWG loader
        ezdxf = self._detect_ezdxf_dwg()
        if ezdxf:
            converters.append(ezdxf)

        # 4. AutoCAD (acad.exe on Windows)
        acad = self._detect_autocad()
        if acad:
            converters.append(acad)

        return converters

    def get_best(self) -> ConverterInfo:
        """Return the best available converter, or None."""
        converters = self.detect_all()
        for c in converters:
            if c.available:
                return c
        return None

    def _detect_libredwg(self) -> ConverterInfo:
        info = ConverterInfo(name="LibreDWG", path="", command="dwg2dxf {input} -o {output}",
                            notes="Open-source DWG library.")
        # Check local tools directory first (bundled), then PATH
        here = os.path.dirname(os.path.abspath(__file__))
        # packages/universal_ingestion/dwg_production.py → 2 levels up = workspace root
        local_exe = os.path.join(os.path.dirname(os.path.dirname(here)),
                                "tools", "libredwg", "dwg2dxf.exe")
        for exe_path in [local_exe, "dwg2dxf", "dwg2dxf.exe"]:
            if isinstance(exe_path, str) and os.path.exists(exe_path):
                info.available = True
                info.path = exe_path
                info.command = f'"{exe_path}" "{{input}}" -o "{{output}}"'
                try:
                    result = subprocess.run([exe_path, "--version"], capture_output=True, text=True, timeout=5)
                    info.version = (result.stdout + result.stderr).strip()[:100]
                except:
                    pass
                return info
        # Try PATH
        try:
            result = subprocess.run(["dwg2dxf", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or "dwg2dxf" in (result.stdout + result.stderr).lower():
                info.available = True
                info.path = shutil.which("dwg2dxf") or "dwg2dxf"
                info.version = (result.stdout + result.stderr).strip()[:100]
        except:
            pass
        return info

    def _detect_oda(self) -> ConverterInfo:
        info = ConverterInfo(name="ODA File Converter", path="",
                            command='ODAFileConverter "{input}" "{output_dir}" ACAD2018 DXF 0 1',
                            notes="Free from opendesign.com/guestfiles/oda_file_converter")
        oda_paths = [
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
            "/usr/bin/ODAFileConverter",
            "/opt/oda/ODAFileConverter",
        ]
        for p in oda_paths:
            if os.path.exists(p):
                info.available = True
                info.path = p
                info.command = f'"{p}" "{{input}}" "{{output_dir}}" ACAD2018 DXF 0 1'
                # For ODA, output_dir is a directory, file gets same name with .dxf
                return info
        # Also check PATH
        found = shutil.which("ODAFileConverter")
        if found:
            info.available = True
            info.path = found
        return info

    def _detect_ezdxf_dwg(self) -> ConverterInfo:
        info = ConverterInfo(name="ezdxf DWG", path="", command="",
                            notes="Python DWG reader via ezdxf. May not support all DWG versions.")
        try:
            from ezdxf.addons import dwg
            # Try to check if DWG loading actually works
            info.available = True
            info.version = f"ezdxf {getattr(dwg, '__version__', 'unknown')}"
        except ImportError:
            pass
        return info

    def _detect_autocad(self) -> ConverterInfo:
        info = ConverterInfo(name="AutoCAD", path="",
                            command='acad.exe /b "{script_path}"',
                            notes="AutoCAD console mode. Requires AutoCAD installation.")
        acad_paths = [
            r"C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
        ]
        for p in acad_paths:
            if os.path.exists(p):
                info.available = True
                info.path = p
                return info
        return info


# ══════════════════ DWG → DXF CONVERTER ══════════════════

class DWGToDXFConverter:
    """Auto-convert DWG to DXF using the best available converter."""

    def __init__(self):
        self.detector = DWGConverterDetector()

    def convert(self, dwg_path: str, output_dir: str = None) -> tuple[str, ConverterInfo, str]:
        """
        Convert DWG to DXF. Returns (dxf_path, converter_info, error_message).
        If conversion fails, returns (None, None, error_message).
        """
        converter = self.detector.get_best()

        if not converter:
            return None, None, (
                "No DWG converter found. Install LibreDWG (dwg2dxf) or ODA File Converter.\n"
                "  LibreDWG: apt install libredwg-tools  or  brew install libredwg\n"
                "  ODA: https://www.opendesign.com/guestfiles/oda_file_converter\n"
                f"  Fallback: heuristic import (reduced fidelity)"
            )

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="v5d_dwg_")

        # Build output path — same name, .dxf extension
        base = os.path.splitext(os.path.basename(dwg_path))[0]
        dxf_path = os.path.join(output_dir, f"{base}.dxf")

        logger.info("dwg_conversion_start",
                     converter=converter.name, input=dwg_path, output=dxf_path)

        try:
            success = self._run_converter(converter, dwg_path, dxf_path, output_dir)
            if success and os.path.exists(dxf_path) and os.path.getsize(dxf_path) > 100:
                logger.info("dwg_conversion_success",
                            converter=converter.name,
                            dxf_size=os.path.getsize(dxf_path))
                return dxf_path, converter, ""
            else:
                return None, converter, "Conversion produced no output or file too small"
        except subprocess.TimeoutExpired:
            return None, converter, f"Converter {converter.name} timed out after 120s"
        except Exception as e:
            logger.error("dwg_conversion_failed", converter=converter.name, error=str(e))
            return None, converter, f"Conversion error: {str(e)[:200]}"

    def _run_converter(self, converter: ConverterInfo, dwg_path: str, dxf_path: str, output_dir: str) -> bool:
        """Execute the converter command."""
        if converter.name == "ODA File Converter":
            return self._run_oda(converter, dwg_path, output_dir, dxf_path)
        elif converter.name == "LibreDWG":
            return self._run_libredwg(converter, dwg_path, dxf_path)
        elif converter.name == "ezdxf DWG":
            return self._run_ezdxf(converter, dwg_path, dxf_path)
        else:
            return False

    def _run_libredwg(self, converter: ConverterInfo, dwg_path: str, dxf_path: str) -> bool:
        cmd = [converter.path, dwg_path, "-o", dxf_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 or os.path.exists(dxf_path)

    def _run_oda(self, converter: ConverterInfo, dwg_path: str, output_dir: str, dxf_path: str) -> bool:
        # ODA outputs to the output directory, not directly to dxf_path
        exe = converter.path
        cmd = [exe, dwg_path, output_dir, "ACAD2018", "DXF", "0", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # ODA creates the DXF in the output dir with same basename
        base = os.path.splitext(os.path.basename(dwg_path))[0]
        generated = os.path.join(output_dir, f"{base}.dxf")
        if os.path.exists(generated) and generated != dxf_path:
            shutil.move(generated, dxf_path)
        return os.path.exists(dxf_path)

    def _run_ezdxf(self, converter: ConverterInfo, dwg_path: str, dxf_path: str) -> bool:
        try:
            from ezdxf.addons.dwg import load
            doc, info = load(dwg_path)
            doc.saveas(dxf_path)
            return os.path.exists(dxf_path)
        except Exception as e:
            logger.error("ezdxf_dwg_failed", error=str(e))
            return False


# ══════════════════ PRODUCTION DWG IMPORTER ══════════════════

class ProductionDWGImporter:
    """
    Production-grade DWG importer with auto-conversion and fallback.

    Priority:
    1. LibreDWG/ODA → auto-convert to DXF → full-fidelity import
    2. Heuristic → reduced-fidelity fallback
    """

    def __init__(self):
        self.converter = DWGToDXFConverter()
        self._heuristic = None  # Lazy

    @property
    def heuristic(self):
        if self._heuristic is None:
            from packages.universal_ingestion.dwg_heuristic import HeuristicDWGImporter
            self._heuristic = HeuristicDWGImporter()
        return self._heuristic

    def import_file(self, data: bytes, filename: str = "", format_info=None):
        """Import DWG with auto-conversion, falling back to heuristic."""
        import time
        t0 = time.time()

        # Save DWG to temp file for converter tools
        tmpdir = tempfile.mkdtemp(prefix="v5d_dwg_import_")
        dwg_tmp = os.path.join(tmpdir, filename or "input.dwg")
        with open(dwg_tmp, "wb") as f:
            f.write(data)

        # ── Try full-fidelity import via converter ──
        dxf_path, converter, error = self.converter.convert(dwg_tmp, tmpdir)

        if dxf_path and os.path.exists(dxf_path):
            with open(dxf_path, "r", errors="ignore") as f:
                dxf_content = f.read()

            if len(dxf_content) > 500:
                from packages.universal_ingestion import DXFImporter
                dxf_importer = DXFImporter()
                geo = dxf_importer.import_file(dxf_content.encode(), os.path.basename(dxf_path))
                geo.source_format = "dwg"
                geo.source_filename = filename
                geo.importer_used = f"ProductionDWGImporter+{converter.name}+DXFImporter"
                geo.import_duration_ms = (time.time() - t0) * 1000
                geo.import_warnings = []
                # Cleanup
                try: os.remove(dwg_tmp); os.remove(dxf_path); os.rmdir(tmpdir)
                except: pass
                return geo

        # ── Fallback: heuristic import ──
        try: os.remove(dwg_tmp)
        except: pass
        try: os.rmdir(tmpdir)
        except: pass

        logger.warn("dwg_falling_back_to_heuristic", filename=filename, error=error[:100] if error else "unknown")

        geo = self.heuristic.import_file(data, filename, format_info)
        geo.import_warnings.append(
            "REDUCED FIDELITY: Heuristic DWG import used. Install LibreDWG or ODA File Converter for full fidelity."
        )
        geo.import_warnings.append(f"Converter error: {error[:200]}" if error else "No converter available")
        geo.import_duration_ms = (time.time() - t0) * 1000
        return geo


# ══════════════════ COMPARISON TOOL ══════════════════

def compare_imports(dwg_path: str) -> dict:
    """Compare heuristic vs full DWG import on the same file."""
    with open(dwg_path, "rb") as f:
        data = f.read()

    print(f"╔{'═'*68}╗")
    print(f"║  DWG IMPORT COMPARISON                                                ║")
    print(f"╚{'═'*68}╝")
    print(f"  File: {dwg_path} ({len(data)/1024:.1f} KB)")

    # Heuristic
    t0 = time.time()
    from packages.universal_ingestion.dwg_heuristic import HeuristicDWGImporter
    heu = HeuristicDWGImporter().import_file(data)
    heu_time = (time.time() - t0) * 1000

    # Production
    t0 = time.time()
    prod = ProductionDWGImporter()
    pro = prod.import_file(data)
    pro_time = (time.time() - t0) * 1000

    # Report
    report = {
        "file": dwg_path,
        "file_size_bytes": len(data),
        "heuristic": {"walls": heu.wall_count, "rooms": heu.room_count,
                       "doors": heu.door_count, "windows": heu.window_count,
                       "labels": len(heu.text_labels), "time_ms": heu_time,
                       "warnings": heu.import_warnings},
        "production": {"walls": pro.wall_count, "rooms": pro.room_count,
                        "doors": pro.door_count, "windows": pro.window_count,
                        "labels": len(pro.text_labels), "time_ms": pro_time,
                        "importer": pro.importer_used, "warnings": pro.import_warnings},
    }

    print(f"\n  {'Metric':20s} {'Heuristic':>12s} {'Production':>12s} {'Delta':>10s}")
    print(f"  {'─'*20} {'─'*12} {'─'*12} {'─'*10}")
    for k, hk, pk in [("Walls", heu.wall_count, pro.wall_count),
                       ("Rooms", heu.room_count, pro.room_count),
                       ("Doors", heu.door_count, pro.door_count),
                       ("Windows", heu.window_count, pro.window_count),
                       ("Labels", len(heu.text_labels), len(pro.text_labels))]:
        delta = pk - hk
        sign = "+" if delta > 0 else ""
        print(f"  {k:20s} {hk:>12d} {pk:>12d} {sign}{delta:>9d}")

    print(f"\n  {'Time':20s} {heu_time:>11.0f}ms {pro_time:>11.0f}ms")
    print(f"  Heuristic: {'⚠ REDUCED FIDELITY' if heu.import_warnings else 'OK'}")
    print(f"  Production: {'✅ FULL FIDELITY' if 'FIDELITY' not in str(pro.import_warnings) else '⚠ REDUCED'}")

    if pro.importer_used and "ProductionDWG" in pro.importer_used:
        print(f"  Converter: {pro.importer_used}")

    return report


# ── Re-register the production importer ──

def register_production_dwg():
    """Register the production DWG importer in the universal ingestion registry."""
    from packages.universal_ingestion import registry, CADFormat
    from packages.universal_ingestion.dwg_heuristic import HeuristicDWGImporter

    # Replace heuristic with production importer
    prod = ProductionDWGImporter()
    # Hack: override the importer's format to CADFormat.DWG
    prod.format = CADFormat.DWG
    registry.register(prod)

    logger.info("production_dwg_registered")
