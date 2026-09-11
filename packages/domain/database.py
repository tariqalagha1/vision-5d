"""Vision 5D — Database Configuration"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Optional
from uuid import UUID
import os

DATABASE_URL = os.getenv(
    "V5D_DATABASE_URL",
    "sqlite:///./vision5d.db"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tenant context for RLS emulation on SQLite
_current_tenant: Optional[UUID] = None

def set_current_tenant(tenant_id: Optional[UUID]):
    global _current_tenant
    _current_tenant = tenant_id

def get_current_tenant() -> Optional[UUID]:
    return _current_tenant

@contextmanager
def tenant_context(tenant_id: UUID):
    """Context manager for tenant-scoped operations."""
    old = _current_tenant
    set_current_tenant(tenant_id)
    try:
        yield
    finally:
        set_current_tenant(old)

def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# On PostgreSQL, set tenant for RLS
@event.listens_for(engine, "connect")
def set_tenant_on_connect(dbapi_connection, connection_record):
    """Set tenant context on PostgreSQL connections for RLS."""
    if "postgresql" in DATABASE_URL and _current_tenant:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET app.current_tenant_id = '{_current_tenant}'")
            cursor.close()
        except Exception:
            pass  # SQLite doesn't support this
