"""Vision 5D — Database Models (SQLAlchemy)"""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum as SAEnum, Integer, Float,
    ForeignKey, UniqueConstraint, Text, LargeBinary, JSON, BigInteger, Index
)
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def new_uuid():
    return uuid.uuid4()


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    external_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settings = Column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(255), nullable=False)
    email = Column(String(255))
    display_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tenant = relationship("Tenant")


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    state = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settings = Column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_workspace_tenant_name"),)


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_ws_member"),)


class Project(Base):
    __tablename__ = "projects"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(200), nullable=False)
    state = Column(String(20), default="DRAFT")
    project_type = Column(String(50), default="other")
    owner_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    settings = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)
    version = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_project_ws_name"),)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permission = Column(String(20), default="read")
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_proj_member"),)


class ProviderConfig(Base):
    __tablename__ = "provider_configs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    provider_type = Column(String(50), nullable=False)
    display_name = Column(String(100))
    base_url = Column(String(500))
    default_model_id = Column(String(100))
    capability_flags = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    connection_status = Column(String(20), default="UNTESTED")
    last_tested_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SecretRef(Base):
    """Opaque reference only — raw key is NEVER in this table"""
    __tablename__ = "secret_refs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    provider_id = Column(PG_UUID(as_uuid=True), ForeignKey("provider_configs.id"), nullable=False)
    secret_version = Column(Integer, default=1)
    key_label = Column(String(100))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rotated_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))


class EncryptedCredential(Base):
    """Secure store — encrypted credentials, separate from application DB ideally"""
    __tablename__ = "encrypted_credentials"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    secret_ref_id = Column(PG_UUID(as_uuid=True), ForeignKey("secret_refs.id"), nullable=False, unique=True)
    encrypted_credential = Column(LargeBinary, nullable=False)
    encryption_key_id = Column(String(255))
    encryption_algo = Column(String(50), default="AES-256-GCM")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    artifact_type = Column(String(100), nullable=False)
    state = Column(String(20), default="CREATED")
    parent_artifact_id = Column(PG_UUID(as_uuid=True), ForeignKey("artifacts.id"))
    content_hash = Column(String(64))
    storage_locator = Column(String(1000))
    content_size_bytes = Column(BigInteger)
    version = Column(Integer, default=1)
    provenance = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DurableJob(Base):
    __tablename__ = "jobs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    job_type = Column(String(100), nullable=False)
    job_version = Column(String(20), default="1.0.0")
    idempotency_key = Column(String(255), unique=True, nullable=False)
    correlation_id = Column(PG_UUID(as_uuid=True), default=new_uuid)
    state = Column(String(30), default="CREATED")
    params = Column(JSON, default=dict)
    param_hash = Column(String(64))
    initiated_by = Column(String(100), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    Index("ix_jobs_tenant", "tenant_id")
    Index("ix_jobs_state", "state")


class JobAttempt(Base):
    __tablename__ = "job_attempts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    worker_id = Column(String(100))
    state = Column(String(30))
    failure_category = Column(String(50))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    attempt_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_attempts.id"))
    sequence = Column(Integer, nullable=False)
    serialized_state = Column(LargeBinary)
    content_hash = Column(String(64))
    state_version = Column(Integer, default=1)
    resume_compatible = Column(Boolean, default=True)
    # Resume metadata
    pipeline_type = Column(String(100))
    current_stage = Column(String(100))
    completed_stages = Column(JSON, default=list)
    input_version_ref = Column(String(255))
    artifact_refs = Column(JSON, default=dict)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    params = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_checkpoints_job", "job_id")
    Index("ix_checkpoints_tenant", "tenant_id")


class ProgressEvent(Base):
    __tablename__ = "progress_events"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    attempt_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_attempts.id"))
    status = Column(String(50))
    progress_pct = Column(Float, default=0.0)
    message = Column(Text)
    current_stage = Column(String(100))
    estimated_remaining_seconds = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class ValidationDecision(Base):
    __tablename__ = "validation_decisions"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    validator_skill_id = Column(String(50))
    target_skill_id = Column(String(50))
    target_artifact_id = Column(PG_UUID(as_uuid=True))
    decision = Column(String(20))
    criteria_met = Column(JSON)
    criteria_failed = Column(JSON)
    evidence_refs = Column(JSON)
    validated_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True))
    event_code = Column(String(50), nullable=False)
    actor_user_id = Column(PG_UUID(as_uuid=True))
    resource_type = Column(String(50))
    resource_id = Column(PG_UUID(as_uuid=True))
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class UploadSession(Base):
    __tablename__ = "upload_sessions"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    state = Column(String(20), default="RECEIVING")
    filename = Column(String(255))
    file_size_bytes = Column(BigInteger)
    content_type = Column(String(100))
    max_chunk_size = Column(Integer, default=10485760)
    total_chunks = Column(Integer, default=0)
    chunks_received = Column(Integer, default=0)
    content_hash = Column(String(64))
    storage_locator = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════
# Phase 2 — Plan Understanding Persistence
# ═══════════════════════════════════════════════════════════

class UnderstandingGraph(Base):
    """Persisted canonical architectural understanding graph."""
    __tablename__ = "understanding_graphs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source_asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("artifacts.id"))
    source_graph_id = Column(PG_UUID(as_uuid=True))  # parent version lineage
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    state = Column(String(20), default="CREATED")
    version = Column(Integer, default=1)
    is_complete = Column(Boolean, default=False)
    completeness_issues = Column(JSON, default=list)
    scale_ratio = Column(String(20))
    scale_confidence = Column(Float, default=0.0)
    graph_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_ugraphs_project", "project_id")
    Index("ix_ugraphs_tenant", "tenant_id")


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("understanding_graphs.id"), nullable=False)
    node_type = Column(String(30), nullable=False)
    label = Column(String(255))
    properties = Column(JSON, default=dict)
    detection_ref = Column(PG_UUID(as_uuid=True))
    confidence = Column(Float, default=1.0)
    source = Column(String(100))
    Index("ix_gnodes_graph", "graph_id")


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("understanding_graphs.id"), nullable=False)
    source_node_id = Column(PG_UUID(as_uuid=True), nullable=False)
    target_node_id = Column(PG_UUID(as_uuid=True), nullable=False)
    edge_type = Column(String(30), nullable=False)
    properties = Column(JSON, default=dict)
    confidence = Column(Float, default=1.0)
    Index("ix_gedges_graph", "graph_id")


# ═══════════════════════════════════════════════════════════
# Phase 3 — Geometry Model Persistence
# ═══════════════════════════════════════════════════════════

class PersistedGeometry(Base):
    """Persisted editable metric floor plan."""
    __tablename__ = "geometry_models"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source_graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("understanding_graphs.id"))
    source_graph_version = Column(Integer, default=1)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    state = Column(String(20), default="CREATED")
    version = Column(Integer, default=1)
    is_complete = Column(Boolean, default=False)
    completeness_issues = Column(JSON, default=list)
    scale_px_per_mm = Column(Float, default=0.0)
    scale_ratio = Column(String(20))
    scale_confidence = Column(Float, default=0.0)
    units = Column(String(10), default="mm")
    model_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    Index("ix_gmodels_project", "project_id")
    Index("ix_gmodels_tenant", "tenant_id")


class GeometryFloor(Base):
    __tablename__ = "geometry_floors"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    model_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_models.id"), nullable=False)
    floor_number = Column(Integer, default=0)
    label = Column(String(100), default="Ground Floor")
    elevation_mm = Column(Float, default=0.0)
    outline = Column(JSON, default=list)
    Index("ix_gfloors_model", "model_id")


class GeometryWall(Base):
    __tablename__ = "geometry_walls"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    floor_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_floors.id"), nullable=False)
    centerline = Column(JSON, nullable=False)  # [[x,y], [x,y], ...]
    face_left = Column(JSON, default=list)
    face_right = Column(JSON, default=list)
    thickness_mm = Column(Float, default=0.0)
    polygon = Column(JSON, default=list)
    is_external = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    state = Column(String(30), default="inferred")
    source_graph_node_id = Column(PG_UUID(as_uuid=True))
    Index("ix_gwalls_floor", "floor_id")


class GeometryRoom(Base):
    __tablename__ = "geometry_rooms"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    floor_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_floors.id"), nullable=False)
    label = Column(String(255))
    function = Column(String(50))
    polygon = Column(JSON, default=list)  # [[x,y], ...] in mm
    area_mm2 = Column(Float, default=0.0)
    area_m2 = Column(Float, default=0.0)
    perimeter_mm = Column(Float, default=0.0)
    centroid_x = Column(Float, default=0.0)
    centroid_y = Column(Float, default=0.0)
    wall_ids = Column(JSON, default=list)
    opening_ids = Column(JSON, default=list)
    adjacent_room_ids = Column(JSON, default=list)
    is_closed = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    state = Column(String(30), default="inferred")
    source_graph_node_id = Column(PG_UUID(as_uuid=True))
    Index("ix_grooms_floor", "floor_id")


class GeometryOpening(Base):
    __tablename__ = "geometry_openings"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    floor_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_floors.id"), nullable=False)
    opening_type = Column(String(20), default="door")
    host_wall_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_walls.id"))
    position_along_wall = Column(Float, default=0.0)
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    width_mm = Column(Float, default=0.0)
    height_mm = Column(Float, default=2100.0)
    orientation_deg = Column(Float, default=0.0)
    swing = Column(String(20), default="unknown")
    sill_height_mm = Column(Float, default=0.0)
    connects_room_a = Column(PG_UUID(as_uuid=True))
    connects_room_b = Column(PG_UUID(as_uuid=True))
    is_valid = Column(Boolean, default=True)
    validation_issues = Column(JSON, default=list)
    confidence = Column(Float, default=1.0)
    state = Column(String(30), default="inferred")
    source_graph_node_id = Column(PG_UUID(as_uuid=True))
    Index("ix_gopenings_floor", "floor_id")


class GeometryEdit(Base):
    """Record of each geometry edit for undo/redo and version history."""
    __tablename__ = "geometry_edits"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    model_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_models.id"), nullable=False)
    edit_type = Column(String(50), nullable=False)
    object_ref = Column(PG_UUID(as_uuid=True))
    params = Column(JSON, default=dict)
    previous_state = Column(JSON)
    version_before = Column(Integer, default=0)
    version_after = Column(Integer, default=0)
    is_undone = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_gedits_model", "model_id")


class DurableArtifactRef(Base):
    __tablename__ = "durable_artifact_refs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    artifact_type = Column(String(100), nullable=False)
    storage_provider = Column(String(50), default="s3")
    storage_key = Column(String(1000), nullable=False)
    content_hash = Column(String(64), nullable=False)
    size_bytes = Column(BigInteger, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    producing_stage = Column(String(100))
    producing_version = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_dartifacts_job", "job_id")
    Index("ix_dartifacts_tenant_project", "tenant_id", "project_id")


# ═══════════════════════════════════════════════════════════
# Phase 4 — 3D Scene Persistence
# ═══════════════════════════════════════════════════════════

class Scene3DVersion(Base):
    __tablename__ = "scene3d_versions"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source_geometry_model_id = Column(PG_UUID(as_uuid=True), ForeignKey("geometry_models.id"))
    source_geometry_version = Column(Integer, default=1)
    source_graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("understanding_graphs.id"))
    source_graph_version = Column(Integer, default=1)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    pipeline_version = Column(String(20), default="4.0.0")
    version = Column(Integer, default=1)
    state = Column(String(20), default="CREATED")
    is_complete = Column(Boolean, default=False)
    completeness_issues = Column(JSON, default=list)
    coordinate_system = Column(String(50), default="mm_right_handed_y_up")
    unit_system = Column(String(10), default="mm")
    lineage = Column(String(500))
    scene_data = Column(JSON, default=dict)
    statistics = Column(JSON, default=dict)
    bbox_min_x = Column(Float); bbox_min_y = Column(Float); bbox_min_z = Column(Float)
    bbox_max_x = Column(Float); bbox_max_y = Column(Float); bbox_max_z = Column(Float)
    vertex_count = Column(Integer, default=0); triangle_count = Column(Integer, default=0)
    artifact_refs = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    Index("ix_scene3d_project", "project_id")
    Index("ix_scene3d_tenant", "tenant_id")
    Index("ix_scene3d_job", "job_id")


class Scene3DObject(Base):
    __tablename__ = "scene3d_objects"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    scene_id = Column(PG_UUID(as_uuid=True), ForeignKey("scene3d_versions.id"), nullable=False)
    object_type = Column(String(50), nullable=False)
    source_id = Column(PG_UUID(as_uuid=True))
    level_id = Column(PG_UUID(as_uuid=True))
    label = Column(String(255))
    properties = Column(JSON, default=dict)
    position_x = Column(Float, default=0.0); position_y = Column(Float, default=0.0); position_z = Column(Float, default=0.0)
    visible = Column(Boolean, default=True)
    mesh_index = Column(Integer)
    Index("ix_scene3dobj_scene", "scene_id")


class Scene3DMesh(Base):
    __tablename__ = "scene3d_meshes"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    scene_id = Column(PG_UUID(as_uuid=True), ForeignKey("scene3d_versions.id"), nullable=False)
    object_id = Column(PG_UUID(as_uuid=True))
    object_type = Column(String(50))
    vertex_count = Column(Integer, default=0); triangle_count = Column(Integer, default=0)
    material_id = Column(PG_UUID(as_uuid=True))
    mesh_data = Column(JSON, default=dict)
    is_valid = Column(Boolean, default=True)
    validation_issues = Column(JSON, default=list)
    Index("ix_scene3dmesh_scene", "scene_id")


# ═══════════════════════════════════════════════════════════
# Phase 5 — Studio Persistence
# ═══════════════════════════════════════════════════════════

class StudioSceneVersion(Base):
    __tablename__ = "studio_versions"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source_scene_id = Column(PG_UUID(as_uuid=True), ForeignKey("scene3d_versions.id"))
    source_scene_version = Column(Integer, default=1)
    parent_studio_version = Column(PG_UUID(as_uuid=True))
    version_number = Column(Integer, default=1)
    name = Column(String(255), default="")
    description = Column(Text, default="")
    state = Column(String(20), default="COMMITTED")
    edit_count = Column(Integer, default=0)
    draft_snapshot = Column(JSON, default=dict)
    lineage = Column(String(500))
    created_by = Column(PG_UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    Index("ix_studio_project", "project_id")
    Index("ix_studio_tenant", "tenant_id")


class StudioDraft(Base):
    __tablename__ = "studio_drafts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source_scene_id = Column(PG_UUID(as_uuid=True), ForeignKey("scene3d_versions.id"))
    source_scene_version = Column(Integer, default=1)
    state = Column(String(20), default="DRAFT")
    draft_data = Column(JSON, default=dict)
    save_counter = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    Index("ix_studio_draft_project", "project_id")


class StudioEditOperation(Base):
    __tablename__ = "studio_edits"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    studio_version_id = Column(PG_UUID(as_uuid=True), ForeignKey("studio_versions.id"))
    draft_id = Column(PG_UUID(as_uuid=True), ForeignKey("studio_drafts.id"))
    user_id = Column(PG_UUID(as_uuid=True))
    target_object_id = Column(PG_UUID(as_uuid=True))
    object_type = Column(String(50))
    operation_type = Column(String(50), nullable=False)
    before_state = Column(JSON, default=dict)
    after_state = Column(JSON, default=dict)
    sequence = Column(Integer, default=0)
    is_undone = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_studioedits_draft", "draft_id")


class FurnitureLibraryItem(Base):
    __tablename__ = "furniture_library"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="generic")
    subcategory = Column(String(50), default="")
    dimensions_w = Column(Float, default=1000)
    dimensions_h = Column(Float, default=800)
    dimensions_d = Column(Float, default=600)
    thumbnail = Column(String(1000))
    source_artifact = Column(String(1000))
    default_material = Column(String(100))
    content_hash = Column(String(64))
    description = Column(Text)
    is_global = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════
# Phase 6 — AI Intelligence
# ═══════════════════════════════════════════════════════════

class AIDesignProposal(Base):
    __tablename__ = "ai_proposals"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    request_id = Column(PG_UUID(as_uuid=True))
    analysis_id = Column(PG_UUID(as_uuid=True))
    source_scene_id = Column(PG_UUID(as_uuid=True), ForeignKey("scene3d_versions.id"))
    source_studio_version = Column(PG_UUID(as_uuid=True), ForeignKey("studio_versions.id"))
    user_text = Column(Text)
    objective = Column(String(50))
    proposal_data = Column(JSON, default=dict)
    provider = Column(String(50), default="simulation")
    model = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    approval_state = Column(String(30), default="pending")
    approved_option_index = Column(Integer)
    approved_edit_ids = Column(JSON, default=list)
    rejected_edit_ids = Column(JSON, default=list)
    ai_branch_draft_id = Column(PG_UUID(as_uuid=True), ForeignKey("studio_drafts.id"))
    ai_branch_version_id = Column(PG_UUID(as_uuid=True), ForeignKey("studio_versions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    Index("ix_aiproposals_project", "project_id")
    Index("ix_aiproposals_tenant", "tenant_id")


class AIProviderRun(Base):
    __tablename__ = "ai_provider_runs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    provider = Column(String(50))
    model = Column(String(100))
    prompt_template = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    response_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AIUsageRecord(Base):
    __tablename__ = "ai_usage"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    provider = Column(String(50))
    model = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    job_id = Column(PG_UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
