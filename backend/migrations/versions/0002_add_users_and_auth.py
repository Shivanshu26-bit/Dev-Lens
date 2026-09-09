"""add users and repository ownership auth schema

Revision ID: 0002_add_users_and_auth
Revises: 0001_initial_schema
Create Date: 2026-09-09 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_users_and_auth'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('github_user_id', sa.String(length=100), nullable=False),
        sa.Column('github_login', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_github_user_id', 'users', ['github_user_id'], unique=True)
    op.create_index('ix_users_github_login', 'users', ['github_login'], unique=False)

    # 2. Update repositories table with user_id and composite uniqueness
    with op.batch_alter_table('repositories') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Uuid(), nullable=True))
        batch_op.drop_index('ix_repositories_github_url')
        batch_op.create_index('ix_repositories_github_url', ['github_url'], unique=False)
        batch_op.create_index('ix_repositories_user_id', ['user_id'], unique=False)
        batch_op.create_index('uq_repositories_user_id_github_url', ['user_id', 'github_url'], unique=True)
        batch_op.create_foreign_key('fk_repositories_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # 3. Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_sessions_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_token_hash', 'user_sessions', ['token_hash'], unique=True)
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'], unique=False)
    op.create_index('ix_user_sessions_is_revoked', 'user_sessions', ['is_revoked'], unique=False)


def downgrade() -> None:
    # 0. Drop user_sessions table
    op.drop_index('ix_user_sessions_is_revoked', table_name='user_sessions')
    op.drop_index('ix_user_sessions_expires_at', table_name='user_sessions')
    op.drop_index('ix_user_sessions_token_hash', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_table('user_sessions')

    # 1. Revert repositories table changes
    with op.batch_alter_table('repositories') as batch_op:
        batch_op.drop_constraint('fk_repositories_user_id_users', type_='foreignkey')
        batch_op.drop_index('uq_repositories_user_id_github_url')
        batch_op.drop_index('ix_repositories_user_id')
        batch_op.drop_index('ix_repositories_github_url')
        batch_op.create_index('ix_repositories_github_url', ['github_url'], unique=True)
        batch_op.drop_column('user_id')

    # 2. Drop users table
    op.drop_index('ix_users_github_login', table_name='users')
    op.drop_index('ix_users_github_user_id', table_name='users')
    op.drop_table('users')
