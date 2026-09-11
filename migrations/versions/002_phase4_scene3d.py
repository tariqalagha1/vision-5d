"""Phase 4 — 3D Scene persistence tables.

Revision ID: 002_phase4_scene3d
Revises: 001_initial
Create Date: 2026-07-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_phase4_scene3d'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scene3d_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_geometry_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geometry_models.id')),
        sa.Column('source_geometry_version', sa.Integer, default=1),
        sa.Column('source_graph_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('understanding_graphs.id')),
        sa.Column('source_graph_version', sa.Integer, default=1),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id')),
        sa.Column('pipeline_version', sa.String(20), default='4.0.0'),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('state', sa.String(20), default='CREATED'),
        sa.Column('is_complete', sa.Boolean, default=False),
        sa.Column('completeness_issues', sa.JSON, default=[]),
        sa.Column('coordinate_system', sa.String(50), default='mm_right_handed_y_up'),
        sa.Column('unit_system', sa.String(10), default='mm'),
        sa.Column('lineage', sa.String(500)),
        sa.Column('scene_data', sa.JSON, default={}),
        sa.Column('statistics', sa.JSON, default={}),
        sa.Column('bbox_min_x', sa.Float), sa.Column('bbox_min_y', sa.Float), sa.Column('bbox_min_z', sa.Float),
        sa.Column('bbox_max_x', sa.Float), sa.Column('bbox_max_y', sa.Float), sa.Column('bbox_max_z', sa.Float),
        sa.Column('vertex_count', sa.Integer, default=0), sa.Column('triangle_count', sa.Integer, default=0),
        sa.Column('artifact_refs', sa.JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_scene3d_project', 'scene3d_versions', ['project_id'])
    op.create_index('ix_scene3d_tenant', 'scene3d_versions', ['tenant_id'])
    op.create_index('ix_scene3d_job', 'scene3d_versions', ['job_id'])

    op.create_table(
        'scene3d_objects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scene_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scene3d_versions.id'), nullable=False),
        sa.Column('object_type', sa.String(50), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True)),
        sa.Column('level_id', postgresql.UUID(as_uuid=True)),
        sa.Column('label', sa.String(255)),
        sa.Column('properties', sa.JSON, default={}),
        sa.Column('position_x', sa.Float, default=0.0), sa.Column('position_y', sa.Float, default=0.0), sa.Column('position_z', sa.Float, default=0.0),
        sa.Column('visible', sa.Boolean, default=True),
        sa.Column('mesh_index', sa.Integer),
    )
    op.create_index('ix_scene3dobj_scene', 'scene3d_objects', ['scene_id'])

    op.create_table(
        'scene3d_meshes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scene_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scene3d_versions.id'), nullable=False),
        sa.Column('object_id', postgresql.UUID(as_uuid=True)),
        sa.Column('object_type', sa.String(50)),
        sa.Column('vertex_count', sa.Integer, default=0), sa.Column('triangle_count', sa.Integer, default=0),
        sa.Column('material_id', postgresql.UUID(as_uuid=True)),
        sa.Column('mesh_data', sa.JSON, default={}),
        sa.Column('is_valid', sa.Boolean, default=True),
        sa.Column('validation_issues', sa.JSON, default=[]),
    )
    op.create_index('ix_scene3dmesh_scene', 'scene3d_meshes', ['scene_id'])


def downgrade() -> None:
    op.drop_table('scene3d_meshes')
    op.drop_table('scene3d_objects')
    op.drop_table('scene3d_versions')
