"""Regression tests for the UUID shadowing bug.

Root cause (fixed): ``packages/domain/models.py`` imported SQLAlchemy's
PostgreSQL type as ``UUID``, and any ``from packages.domain.models import *``
re-bound ``UUID`` to that type — shadowing stdlib ``uuid.UUID``. The worker
then built a SQLAlchemy type object instead of a UUID, which pydantic rejected.

Fix: the SQLAlchemy type is aliased as ``PG_UUID`` so star imports can no
longer shadow ``uuid.UUID``.
"""

import uuid


def test_domain_models_does_not_export_uuid_name():
    """The module must not expose a ``UUID`` name that star imports would leak."""
    import packages.domain.models as dm
    assert not hasattr(dm, "UUID"), (
        "packages.domain.models leaks a 'UUID' name (SQLAlchemy type); "
        "it must be aliased as PG_UUID so `import *` cannot shadow stdlib uuid.UUID"
    )


def test_star_import_preserves_stdlib_uuid():
    """A star import must leave the UUID symbol as stdlib uuid.UUID (or absent)."""
    ns = {}
    exec("from packages.domain.models import *", ns)
    assert ns.get("UUID", uuid.UUID) is uuid.UUID, (
        "`from packages.domain.models import *` shadowed uuid.UUID with "
        f"{type(ns.get('UUID')).__module__}.{type(ns.get('UUID')).__name__}"
    )


def test_pg_uuid_alias_exists():
    """The SQLAlchemy UUID type should be available under its PG_UUID alias."""
    import packages.domain.models as dm
    assert hasattr(dm, "PG_UUID"), "SQLAlchemy UUID type should be aliased as PG_UUID"
