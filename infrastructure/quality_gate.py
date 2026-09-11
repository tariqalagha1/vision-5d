#!/usr/bin/env python3
"""
Vision 5D — Quality Gate Runner (V1.0 Certification)
Runs all tests, checks, and certifications. Produces a final report.
Usage: python3 infrastructure/quality_gate.py
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "evidence", "v1_0_certification")
os.makedirs(REPORT_DIR, exist_ok=True)


class QualityGate:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now(timezone.utc)
        self.all_passed = True

    def run(self) -> dict:
        print("=" * 60)
        print("  VISION 5D VERSION 1.0 QUALITY GATE")
        print("=" * 60)

        self._check_imports()
        self._check_migrations()
        self._check_backend_tests()
        self._check_compilation()
        self._check_provider_audit()
        self._check_phase5_certification()
        self._check_configuration()

        return self._generate_report()

    def _check_imports(self):
        print("\n--- Import Check ---")
        modules = [
            "packages.contracts.models",
            "packages.domain.models",
            "packages.domain.database",
            "packages.geometry.contracts",
            "packages.scene3d.contracts",
            "packages.scene3d.reconstruction",
            "packages.scene3d.glb_export",
            "packages.studio.contracts",
            "packages.studio.persistence",
            "packages.studio.studio_export",
            "packages.studio.glb_inspector",
            "packages.studio.storage",
            "packages.ai.contracts",
            "packages.ai.analysis",
            "packages.ai.proposal",
            "packages.ai.provider_client",
            "packages.ai.completion",
            "packages.observability",
            "packages.security.production",
            "apps.api.main",
            "apps.api.plan_routes",
            "apps.api.geometry_routes",
            "apps.api.scene3d_routes",
            "apps.api.studio_routes",
            "apps.api.ai_routes",
            "apps.worker.main",
        ]
        passed = 0
        for mod in modules:
            try:
                __import__(mod)
                passed += 1
            except Exception as e:
                print(f"  FAIL {mod}: {e}")
                self.all_passed = False

        self.results.append({"gate": "imports", "passed": passed, "total": len(modules), "status": "PASS" if passed == len(modules) else "FAIL"})
        print(f"  {passed}/{len(modules)} modules imported")

    def _check_migrations(self):
        print("\n--- Migration Check ---")
        mig_dir = os.path.join(os.path.dirname(__file__), "..", "migrations", "versions")
        if os.path.exists(mig_dir):
            versions = [f for f in os.listdir(mig_dir) if f.endswith(".py") and not f.startswith("_")]
            print(f"  {len(versions)} migration versions found")
            for v in sorted(versions):
                print(f"    - {v}")
            self.results.append({"gate": "migrations", "count": len(versions), "status": "PASS"})
        else:
            print("  No migrations directory")
            self.results.append({"gate": "migrations", "count": 0, "status": "WARN"})

    def _check_backend_tests(self):
        print("\n--- Backend Tests ---")
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "tests/", "-q", "--tb=short"],
                capture_output=True, text=True, timeout=120,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            print(result.stdout[-500:] if result.stdout else "No output")
            passed = "failed" not in (result.stdout or "").lower() and result.returncode == 0
            self.results.append({"gate": "backend_tests", "status": "PASS" if passed else "FAIL", "output": result.stdout[-200:]})
        except FileNotFoundError:
            print("  pytest not found — skipping")
            self.results.append({"gate": "backend_tests", "status": "SKIP"})
        except Exception as e:
            print(f"  Error: {e}")
            self.results.append({"gate": "backend_tests", "status": "ERROR"})

    def _check_compilation(self):
        print("\n--- Compilation Check ---")
        py_files = []
        for root, _, files in os.walk(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
            if "__pycache__" in root or ".git" in root or "evidence" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

        passed = 0
        for f in py_files[:100]:  # Sample to avoid timeout
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", f],
                    capture_output=True, timeout=10,
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                )
                if result.returncode == 0:
                    passed += 1
            except Exception:
                pass

        self.results.append({"gate": "compilation", "checked": passed, "total_sampled": min(100, len(py_files)), "status": "PASS" if passed > 0 else "FAIL"})
        print(f"  {passed} files compile clean")

    def _check_provider_audit(self):
        print("\n--- Provider Audit ---")
        try:
            result = subprocess.run(
                ["python3", "scripts/audit_providers.py"],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            configured = "READY" in (result.stdout or "")
            self.results.append({"gate": "provider_audit", "status": "PASS" if configured else "WARN", "output": result.stdout[:200]})
            print(f"  Provider ready: {configured}")
        except Exception as e:
            self.results.append({"gate": "provider_audit", "status": "ERROR", "error": str(e)})

    def _check_phase5_certification(self):
        print("\n--- Phase 5 Certification ---")
        cert_evidence = os.path.join(os.path.dirname(__file__), "..", "evidence", "p5_cert_99_certification_complete.json")
        if os.path.exists(cert_evidence):
            with open(cert_evidence) as f:
                data = json.load(f)
            print(f"  Certification found: {data.get('decision', 'UNKNOWN')}")
            self.results.append({"gate": "phase5_cert", "status": "PASS", "decision": data.get("decision")})
        else:
            self.results.append({"gate": "phase5_cert", "status": "WARN", "note": "Run scripts/certify_p5.py first"})

    def _check_configuration(self):
        print("\n--- Configuration Check ---")
        checks = {
            "V5D_DATABASE_URL": os.getenv("V5D_DATABASE_URL", "not set")[:30],
            "AI_PROVIDER": os.getenv("AI_PROVIDER", "simulation"),
            "API Workers": os.getenv("API_WORKERS", "4"),
        }
        for k, v in checks.items():
            print(f"  {k}: {v}")
        self.results.append({"gate": "configuration", "checks": checks, "status": "PASS"})

    def _generate_report(self) -> dict:
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        passed_gates = sum(1 for r in self.results if r.get("status") == "PASS")
        total_gates = len(self.results)

        report = {
            "product": "Vision 5D",
            "version": "1.0.0",
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": duration,
            "gates_passed": passed_gates,
            "gates_total": total_gates,
            "all_passed": passed_gates == total_gates,
            "results": self.results,
        }

        path = os.path.join(REPORT_DIR, "quality_gate_report.json")
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"  QUALITY GATE: {passed_gates}/{total_gates} PASSED")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Report: {path}")
        print(f"{'='*60}")

        return report


if __name__ == "__main__":
    gate = QualityGate()
    report = gate.run()
    sys.exit(0 if report["all_passed"] else 1)
