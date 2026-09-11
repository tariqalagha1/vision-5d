#!/usr/bin/env python3
"""
Vision 5D — Production Backup Script
Backs up database, artifacts, and exports.
Usage: python3 infrastructure/backup.py
"""
import os, sys, shutil, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKUP_DIR = os.getenv("V5D_BACKUP_DIR", "/app/backups")
DB_URL = os.getenv("V5D_DATABASE_URL", "sqlite:///./vision5d.db")
STORAGE_DIR = os.getenv("V5D_STORAGE_DIR", "/app/.storage")
EXPORTS_DIR = os.getenv("V5D_EXPORTS_DIR", "/app/.exports")
KEEP_DAYS = int(os.getenv("V5D_BACKUP_KEEP_DAYS", "30"))


def backup():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"vision5d_backup_{ts}")
    os.makedirs(backup_path, exist_ok=True)
    manifest = {"timestamp": ts, "backup_id": f"backup_{ts}", "files": {}}

    print(f"[backup] Starting backup to {backup_path}")

    # 1. Database dump
    db_path = None
    if "sqlite" in DB_URL:
        db_path = DB_URL.replace("sqlite:///", "").replace("./", os.path.join(os.path.dirname(__file__), "..") + "/")
        if os.path.exists(db_path):
            dest = os.path.join(backup_path, "database.db")
            shutil.copy2(db_path, dest)
            manifest["files"]["database"] = {"path": dest, "size": os.path.getsize(dest), "hash": file_hash(dest)}
            print(f"[backup] Database: {os.path.getsize(dest)} bytes")
    else:
        # PostgreSQL dump
        import subprocess
        dest = os.path.join(backup_path, "database.sql")
        db_user = os.getenv("DB_USER", "vision5d")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "postgres")
        db_name = os.getenv("DB_NAME", "vision5d")
        env = os.environ.copy()
        env["PGPASSWORD"] = db_pass
        result = subprocess.run(
            ["pg_dump", "-h", db_host, "-U", db_user, "-d", db_name, "-f", dest],
            env=env, capture_output=True, text=True
        )
        if result.returncode == 0:
            manifest["files"]["database"] = {"path": dest, "size": os.path.getsize(dest), "hash": file_hash(dest)}
            print(f"[backup] Database dumped: {os.path.getsize(dest)} bytes")
        else:
            print(f"[backup] Database dump FAILED: {result.stderr}")

    # 2. Storage artifacts
    storage_backup = os.path.join(backup_path, "storage")
    if os.path.exists(STORAGE_DIR):
        shutil.copytree(STORAGE_DIR, storage_backup, dirs_exist_ok=True)
        total_size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, files in os.walk(storage_backup) for f in files)
        manifest["files"]["storage"] = {"path": storage_backup, "size": total_size, "file_count": len(list(Path(storage_backup).rglob("*")))}
        print(f"[backup] Storage: {total_size} bytes")

    # 3. Exports
    exports_backup = os.path.join(backup_path, "exports")
    if os.path.exists(EXPORTS_DIR):
        shutil.copytree(EXPORTS_DIR, exports_backup, dirs_exist_ok=True)
        total_size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, files in os.walk(exports_backup) for f in files)
        manifest["files"]["exports"] = {"path": exports_backup, "size": total_size, "file_count": len(list(Path(exports_backup).rglob("*")))}
        print(f"[backup] Exports: {total_size} bytes")

    # 4. Write manifest
    manifest_path = os.path.join(backup_path, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[backup] Manifest: {manifest_path}")

    # 5. Cleanup old backups
    cleanup_old_backups()

    print(f"[backup] Backup complete: {backup_path}")
    return manifest


def file_hash(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def cleanup_old_backups():
    """Remove backups older than KEEP_DAYS."""
    now = datetime.now(timezone.utc)
    for entry in sorted(os.listdir(BACKUP_DIR)):
        entry_path = os.path.join(BACKUP_DIR, entry)
        if not os.path.isdir(entry_path) or not entry.startswith("vision5d_backup_"):
            continue
        try:
            ts_str = entry.replace("vision5d_backup_", "")
            ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            age = (now - ts.replace(tzinfo=timezone.utc)).days
            if age > KEEP_DAYS:
                shutil.rmtree(entry_path)
                print(f"[backup] Removed old backup: {entry} ({age}d old)")
        except (ValueError, OSError):
            continue


def verify_backup(backup_id: str) -> dict:
    """Verify a backup manifest and file integrity."""
    backup_path = os.path.join(BACKUP_DIR, f"vision5d_backup_{backup_id}")
    manifest_path = os.path.join(backup_path, "manifest.json")
    if not os.path.exists(manifest_path):
        return {"verified": False, "error": "Manifest not found"}

    with open(manifest_path) as f:
        manifest = json.load(f)

    results = []
    for name, info in manifest.get("files", {}).items():
        path = info.get("path", "")
        expected_hash = info.get("hash", "")
        if os.path.exists(path) and expected_hash:
            actual = file_hash(path)
            results.append({"file": name, "match": actual == expected_hash, "hash": actual[:16]})

    all_ok = all(r["match"] for r in results)
    return {"verified": all_ok, "backup_id": backup_id, "results": results}


if __name__ == "__main__":
    result = backup()
    if result:
        print(json.dumps(result, indent=2))
