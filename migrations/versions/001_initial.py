"""Initial migration — Phase 1 tenant, workspace, project, provider, job, and artifact tables.

Revision ID: 001_initial
Create Date: 2026-07-24

This migration creates the base tenant-isolated schema:
  - tenants, users
  - workspaces, workspace_memberships
  - projects, project_memberships
  - provider_configs, secret_refs, encrypted_credentials
  - artifacts, jobs, job_attempts, checkpoints, progress_events
  - validation_decisions, audit_events, upload_sessions
  - understanding_graphs, graph_nodes, graph_edges
  - geometry_models, geometry_floors, geometry_walls, geometry_rooms, geometry_openings, geometry_edits
  - durable_artifact_refs
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants and Users
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('settings', sa.JSON, default={}),
    )
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('display_name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('state', sa.String(20), default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('settings', sa.JSON, default={}),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_workspace_tenant_name'),
    )
    op.create_table(
        'workspace_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(20), default='member'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_ws_member'),
    )

    # Projects
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('state', sa.String(20), default='DRAFT'),
        sa.Column('project_type', sa.String(50), default='other'),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('settings', sa.JSON, default={}),
        sa.Column('metadata', sa.JSON, default={}),
        sa.Column('version', sa.Integer, default=1),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_project_ws_name'),
    )
    op.create_table(
        'project_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('permission', sa.String(20), default='read'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_proj_member'),
    )

    # Provider configs
    op.create_table(
        'provider_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100)),
        sa.Column('base_url', sa.String(500)),
        sa.Column('default_model_id', sa.String(100)),
        sa.Column('capability_flags', sa.JSON, default={}),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('connection_status', sa.String(20), default='UNTESTED'),
        sa.Column('last_tested_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'secret_refs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('provider_configs.id'), nullable=False),
        sa.Column('secret_version', sa.Integer, default=1),
        sa.Column('key_label', sa.String(100)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('rotated_at', sa.DateTime(timezone=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'encrypted_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('secret_ref_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('secret_refs.id'), nullable=False, unique=True),
        sa.Column('encrypted_credential', sa.LargeBinary, nullable=False),
        sa.Column('encryption_key_id', sa.String(255)),
        sa.Column('encryption_algo', sa.String(50), default='AES-256-GCM'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Artifacts
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id')),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('state', sa.String(20), default='CREATED'),
        sa.Column('parent_artifact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('artifacts.id')),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('storage_locator', sa.String(1000)),
        sa.Column('content_size_bytes', sa.BigInteger),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('provenance', sa.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Jobs
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id')),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('job_version', sa.String(20), default='1.0.0'),
        sa.Column('idempotency_key', sa.String(255), unique=True, nullable=False),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('state', sa.String(30), default='CREATED'),
        sa.Column('params', sa.JSON, default={}),
        sa.Column('param_hash', sa.String(64)),
        sa.Column('initiated_by', sa.String(100), default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_jobs_tenant', 'jobs', ['tenant_id'])
    op.create_index('ix_jobs_state', 'jobs', ['state'])

    op.create_table(
        'job_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('attempt_number', sa.Integer, default=1),
        sa.Column('worker_id', sa.String(100)),
        sa.Column('state', sa.String(30)),
        sa.Column('failure_category', sa.String(50)),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_attempts.id')),
        sa.Column('sequence', sa.Integer, nullable=False),
        sa.Column('serialized_state', sa.LargeBinary),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('state_version', sa.Integer, default=1),
        sa.Column('resume_compatible', sa.Boolean, default=True),
        sa.Column('pipeline_type', sa.String(100)),
        sa.Column('current_stage', sa.String(100)),
        sa.Column('completed_stages', sa.JSON, default=[]),
        sa.Column('input_version_ref', sa.String(255)),
        sa.Column('artifact_refs', sa.JSON, default={}),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id')),
        sa.Column('params', sa.JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_checkpoints_job', 'checkpoints', ['job_id'])
    op.create_index('ix_checkpoints_tenant', 'checkpoints', ['tenant_id'])

    op.create_table(
        'progress_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_attempts.id')),
        sa.Column('status', sa.String(50)),
        sa.Column('progress_pct', sa.Float, default=0.0),
        sa.Column('message', sa.Text),
        sa.Column('current_stage', sa.String(100)),
        sa.Column('estimated_remaining_seconds', sa.Integer),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'validation_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('validator_skill_id', sa.String(50)),
        sa.Column('target_skill_id', sa.String(50)),
        sa.Column('target_artifact_id', postgresql.UUID(as_uuid=True)),
        sa.Column('decision', sa.String(20)),
        sa.Column('criteria_met', sa.JSON),
        sa.Column('criteria_failed', sa.JSON),
        sa.Column('evidence_refs', sa.JSON),
        sa.Column('validated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True)),
        sa.Column('event_code', sa.String(50), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('details', sa.JSON),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'upload_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('state', sa.String(20), default='RECEIVING'),
        sa.Column('filename', sa.String(255)),
        sa.Column('file_size_bytes', sa.BigInteger),
        sa.Column('content_type', sa.String(100)),
        sa.Column('max_chunk_size', sa.Integer, default=10485760),
        sa.Column('total_chunks', sa.Integer, default=0),
        sa.Column('chunks_received', sa.Integer, default=0),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('storage_locator', sa.String(1000)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Phase 2 — Understanding Graphs
    op.create_table(
        'understanding_graphs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('artifacts.id')),
        sa.Column('source_graph_id', postgresql.UUID(as_uuid=True)),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id')),
        sa.Column('state', sa.String(20), default='CREATED'),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('is_complete', sa.Boolean, default=False),
        sa.Column('completeness_issues', sa.JSON, default=[]),
        sa.Column('scale_ratio', sa.String(20)),
        sa.Column('scale_confidence', sa.Float, default=0.0),
        sa.Column('metadata', sa.JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_ugraphs_project', 'understanding_graphs', ['project_id'])
    op.create_index('ix_ugraphs_tenant', 'understanding_graphs', ['tenant_id'])

    op.create_table(
        'graph_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('graph_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('understanding_graphs.id'), nullable=False),
        sa.Column('node_type', sa.String(30), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('properties', sa.JSON, default={}),
        sa.Column('detection_ref', postgresql.UUID(as_uuid=True)),
        sa.Column('confidence', sa.Float, default=1.0),
        sa.Column('source', sa.String(100)),
    )
    op.create_index('ix_gnodes_graph', 'graph_nodes', ['graph_id'])

    op.create_table(
        'graph_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('graph_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('understanding_graphs.id'), nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edge_type', sa.String(30), nullable=False),
        sa.Column('properties', sa.JSON, default={}),
        sa.Column('confidence', sa.Float, default=1.0),
    )
    op.create_index('ix_gedges_graph', 'graph_edges', ['graph_id'])

    # Phase 3 — Geometry
    op.create_table(
        'geometry_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_graph_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('understanding_graphs.id')),
        sa.Column('source_graph_version', sa.Integer, default=1),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id')),
        sa.Column('state', sa.String(20), default='CREATED'),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('is_complete', sa.Boolean, default=False),
        sa.Column('completeness_issues', sa.JSON, default=[]),
        sa.Column('scale_px_per_mm', sa.Float, default=0.0),
        sa.Column('scale_ratio', sa.String(20)),
        sa.Column('scale_confidence', sa.Float, default=0.0),
        sa.Column('units', sa.String(10), default='mm'),
        sa.Column('metadata', sa.JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_gmodels_project', 'geometry_models', ['project_id'])
    op.create_index('ix_gmodels_tenant', 'geometry_models', ['tenant_id'])

    op.create_table(
        'geometry_floors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_models.id'), nullable=False),
        sa.Column('floor_number', sa.Integer, default=0),
        sa.Column('label', sa.String(100), default='Ground Floor'),
        sa.Column('elevation_mm', sa.Float, default=0.0),
        sa.Column('outline', sa.JSON, default=[]),
    )
    op.create_index('ix_gfloors_model', 'geometry_floors', ['model_id'])

    op.create_table(
        'geometry_walls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_floors.id'), nullable=False),
        sa.Column('centerline', sa.JSON, nullable=False),
        sa.Column('face_left', sa.JSON, default=[]),
        sa.Column('face_right', sa.JSON, default=[]),
        sa.Column('thickness_mm', sa.Float, default=0.0),
        sa.Column('polygon', sa.JSON, default=[]),
        sa.Column('is_external', sa.Boolean, default=False),
        sa.Column('confidence', sa.Float, default=1.0),
        sa.Column('state', sa.String(30), default='inferred'),
        sa.Column('source_graph_node_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_index('ix_gwalls_floor', 'geometry_walls', ['floor_id'])

    op.create_table(
        'geometry_rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_floors.id'), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('function', sa.String(50)),
        sa.Column('polygon', sa.JSON, default=[]),
        sa.Column('area_mm2', sa.Float, default=0.0),
        sa.Column('area_m2', sa.Float, default=0.0),
        sa.Column('perimeter_mm', sa.Float, default=0.0),
        sa.Column('centroid_x', sa.Float, default=0.0),
        sa.Column('centroid_y', sa.Float, default=0.0),
        sa.Column('wall_ids', sa.JSON, default=[]),
        sa.Column('opening_ids', sa.JSON, default=[]),
        sa.Column('adjacent_room_ids', sa.JSON, default=[]),
        sa.Column('is_closed', sa.Boolean, default=False),
        sa.Column('confidence', sa.Float, default=1.0),
        sa.Column('state', sa.String(30), default='inferred'),
        sa.Column('source_graph_node_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_index('ix_grooms_floor', 'geometry_rooms', ['floor_id'])

    op.create_table(
        'geometry_openings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_floors.id'), nullable=False),
        sa.Column('opening_type', sa.String(20), default='door'),
        sa.Column('host_wall_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_walls.id')),
        sa.Column('position_along_wall', sa.Float, default=0.0),
        sa.Column('position_x', sa.Float, default=0.0),
        sa.Column('position_y', sa.Float, default=0.0),
        sa.Column('width_mm', sa.Float, default=0.0),
        sa.Column('height_mm', sa.Float, default=2100.0),
        sa.Column('orientation_deg', sa.Float, default=0.0),
        sa.Column('swing', sa.String(20), default='unknown'),
        sa.Column('sill_height_mm', sa.Float, default=0.0),
        sa.Column('connects_room_a', postgresql.UUID(as_uuid=True)),
        sa.Column('connects_room_b', postgresql.UUID(as_uuid=True)),
        sa.Column('is_valid', sa.Boolean, default=True),
        sa.Column('validation_issues', sa.JSON, default=[]),
        sa.Column('confidence', sa.Float, default=1.0),
        sa.Column('state', sa.String(30), default='inferred'),
        sa.Column('source_graph_node_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_index('ix_gopenings_floor', 'geometry_openings', ['floor_id'])

    op.create_table(
        'geometry_edits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_models.id'), nullable=False),
        sa.Column('edit_type', sa.String(50), nullable=False),
        sa.Column('object_ref', postgresql.UUID(as_uuid=True)),
        sa.Column('params', sa.JSON, default={}),
        sa.Column('previous_state', sa.JSON),
        sa.Column('version_before', sa.Integer, default=0),
        sa.Column('version_after', sa.Integer, default=0),
        sa.Column('is_undone', sa.Boolean, default=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_gedits_model', 'geometry_edits', ['model_id'])

    # Durable Artifact References
    op.create_table(
        'durable_artifact_refs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('storage_provider', sa.String(50), default='s3'),
        sa.Column('storage_key', sa.String(1000), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('size_bytes', sa.BigInteger, default=0),
        sa.Column('mime_type', sa.String(100), default='application/octet-stream'),
        sa.Column('producing_stage', sa.String(100)),
        sa.Column('producing_version', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_dartifacts_job', 'durable_artifact_refs', ['job_id'])
    op.create_index('ix_dartifacts_tenant_project', 'durable_artifact_refs', ['tenant_id', 'project_id'])


def downgrade() -> None:
    op.drop_table('durable_artifact_refs')
    op.drop_table('geometry_edits')
    op.drop_table('geometry_openings')
    op.drop_table('geometry_rooms')
    op.drop_table('geometry_walls')
    op.drop_table('geometry_floors')
    op.drop_table('geometry_models')
    op.drop_table('graph_edges')
    op.drop_table('graph_nodes')
    op.drop_table('understanding_graphs')
    op.drop_table('upload_sessions')
    op.drop_table('audit_events')
    op.drop_table('validation_decisions')
    op.drop_table('progress_events')
    op.drop_table('checkpoints')
    op.drop_table('job_attempts')
    op.drop_table('jobs')
    op.drop_table('artifacts')
    op.drop_table('encrypted_credentials')
    op.drop_table('secret_refs')
    op.drop_table('provider_configs')
    op.drop_table('project_memberships')
    op.drop_table('projects')
    op.drop_table('workspace_memberships')
    op.drop_table('workspaces')
    op.drop_table('users')
    op.drop_table('tenants')
