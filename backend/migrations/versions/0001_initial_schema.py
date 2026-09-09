"""initial schema for repositories and analysis_runs

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-09 15:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Cross-dialect JSONB type
jsonb_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # 1. Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('github_url', sa.String(length=512), nullable=False),
        sa.Column('owner', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('default_branch', sa.String(length=255), nullable=True, server_default='main'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('forks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_issues', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('language', sa.String(length=100), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_repositories_github_url', 'repositories', ['github_url'], unique=True)
    op.create_index('ix_repositories_owner', 'repositories', ['owner'], unique=False)
    op.create_index('ix_repositories_name', 'repositories', ['name'], unique=False)
    op.create_index('ix_repositories_owner_name', 'repositories', ['owner', 'name'], unique=False)

    # 2. Create analysis_runs table
    op.create_table(
        'analysis_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('repository_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('analysis_type', sa.String(length=50), nullable=False, server_default='deterministic'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('deterministic_result', jsonb_type, nullable=True),
        sa.Column('ai_result', jsonb_type, nullable=True),
        sa.Column('metrics', jsonb_type, nullable=True),
        sa.Column('findings', jsonb_type, nullable=True),
        sa.Column('languages', jsonb_type, nullable=True),
        sa.Column('metadata_json', jsonb_type, nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analysis_runs_repository_id', 'analysis_runs', ['repository_id'], unique=False)
    op.create_index('ix_analysis_runs_status', 'analysis_runs', ['status'], unique=False)
    op.create_index('ix_analysis_runs_created_at', 'analysis_runs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_analysis_runs_created_at', table_name='analysis_runs')
    op.drop_index('ix_analysis_runs_status', table_name='analysis_runs')
    op.drop_index('ix_analysis_runs_repository_id', table_name='analysis_runs')
    op.drop_table('analysis_runs')

    op.drop_index('ix_repositories_owner_name', table_name='repositories')
    op.drop_index('ix_repositories_name', table_name='repositories')
    op.drop_index('ix_repositories_owner', table_name='repositories')
    op.drop_index('ix_repositories_github_url', table_name='repositories')
    op.drop_table('repositories')
