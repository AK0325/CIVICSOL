"""Notifications and performance indexes migration

Revision ID: 20261029_002
Revises: 20261029_001
Create Date: 2026-10-29 21:15:00.000000

Schema extensions:
1. Create 'notifications' table for in-app citizen and officer alerts.
2. Add performance query indexes on 'civic_issues' (status, category, priority, created_at).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261029_002'
down_revision: Union[str, None] = '20261029_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------
    # 1. CREATE NOTIFICATIONS TABLE
    # -----------------------------------------------------
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True, server_default='CIVIC_ISSUE'),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'], unique=False)
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'], unique=False)
    op.create_index('ix_notifications_type', 'notifications', ['notification_type'], unique=False)

    # -----------------------------------------------------
    # 2. CREATE PERFORMANCE INDEXES ON CIVIC_ISSUES
    # -----------------------------------------------------
    # Helper to check if index exists before creating
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('civic_issues')]

    if 'ix_civic_issues_status' not in existing_indexes:
        op.create_index('ix_civic_issues_status', 'civic_issues', ['status'], unique=False)

    if 'ix_civic_issues_category' not in existing_indexes:
        op.create_index('ix_civic_issues_category', 'civic_issues', ['category'], unique=False)

    if 'ix_civic_issues_priority' not in existing_indexes:
        op.create_index('ix_civic_issues_priority', 'civic_issues', ['priority'], unique=False)

    if 'ix_civic_issues_created_at' not in existing_indexes:
        op.create_index('ix_civic_issues_created_at', 'civic_issues', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop performance indexes
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('civic_issues')]

    for idx_name in [
        'ix_civic_issues_created_at',
        'ix_civic_issues_priority',
        'ix_civic_issues_category',
        'ix_civic_issues_status',
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='civic_issues')

    # Drop notifications table and indexes
    op.drop_index('ix_notifications_type', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_id', table_name='notifications')
    op.drop_table('notifications')
