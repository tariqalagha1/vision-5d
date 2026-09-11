"""Phase 5 — Studio tables.

Revision ID: 003_phase5_studio
Revises: 002_phase4_scene3d
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_phase5_studio'
down_revision: Union[str, None] = '002_phase4_scene3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('studio_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_scene_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scene3d_versions.id')),
        sa.Column('source_scene_version', sa.Integer, default=1),
        sa.Column('parent_studio_version', postgresql.UUID(as_uuid=True)),
        sa.Column('version_number', sa.Integer, default=1),
        sa.Column('name', sa.String(255)), sa.Column('description', sa.Text),
        sa.Column('state', sa.String(20), default='COMMITTED'),
        sa.Column('edit_count', sa.Integer, default=0),
        sa.Column('draft_snapshot', sa.JSON, default={}),
        sa.Column('lineage', sa.String(500)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_studio_project', 'studio_versions', ['project_id'])
    op.create_index('ix_studio_tenant', 'studio_versions', ['tenant_id'])

    op.create_table('studio_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_scene_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scene3d_versions.id')),
        sa.Column('source_scene_version', sa.Integer, default=1),
        sa.Column('state', sa.String(20), default='DRAFT'),
        sa.Column('draft_data', sa.JSON, default={}),
        sa.Column('save_counter', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_studio_draft_project', 'studio_drafts', ['project_id'])

    op.create_table('studio_edits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('studio_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('studio_versions.id')),
        sa.Column('draft_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('studio_drafts.id')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_object_id', postgresql.UUID(as_uuid=True)),
        sa.Column('object_type', sa.String(50)),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('before_state', sa.JSON, default={}),
        sa.Column('after_state', sa.JSON, default={}),
        sa.Column('sequence', sa.Integer, default=0),
        sa.Column('is_undone', sa.Boolean, default=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_studioedits_draft', 'studio_edits', ['draft_id'])

    op.create_table('furniture_library',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), default='generic'),
        sa.Column('subcategory', sa.String(50)),
        sa.Column('dimensions_w', sa.Float, default=1000),
        sa.Column('dimensions_h', sa.Float, default=800),
        sa.Column('dimensions_d', sa.Float, default=600),
        sa.Column('thumbnail', sa.String(1000)),
        sa.Column('source_artifact', sa.String(1000)),
        sa.Column('default_material', sa.String(100)),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('description', sa.Text),
        sa.Column('is_global', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('furniture_library')
    op.drop_table('studio_edits')
    op.drop_table('studio_drafts')
    op.drop_table('studio_versions')
