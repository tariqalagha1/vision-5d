#!/usr/bin/env python3
"""
Vision 5D — Migration Runner
Run this to apply/verify Alembic migrations.
Usage:
  python3 scripts/run_migration.py upgrade    # Apply migrations
  python3 scripts/run_migration.py downgrade  # Rollback
  python3 scripts/run_migration.py verify     # Verify migration state
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command


def run_upgrade():
    """Apply all pending migrations."""
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    print("Migration upgrade complete.")


def run_downgrade():
    """Rollback last migration."""
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.downgrade(alembic_cfg, "-1")
    print("Migration downgrade complete.")


def verify():
    """Verify current migration state."""
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.current(alembic_cfg)
    print("Migration verification complete.")


def stamp_head():
    """Stamp the database as 'head' without running migrations (for existing DBs)."""
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.stamp(alembic_cfg, "head")
    print("Database stamped at head.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_migration.py [upgrade|downgrade|verify|stamp]")
        sys.exit(1)
    action = sys.argv[1]
    if action == "upgrade":
        run_upgrade()
    elif action == "downgrade":
        run_downgrade()
    elif action == "verify":
        verify()
    elif action == "stamp":
        stamp_head()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
