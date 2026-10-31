"""AI analysis table migration

Revision ID: 20261030_003
Revises: 20261029_002
Create Date: 2026-10-30 16:40:00.000000

Schema extensions:
1. Create 'ai_analyses' table for storing computer vision detections,
   Gemini LLM descriptions, explainable severity/priority scores,
   department recommendations, and authority approval audit state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261030_003'
down_revision: Union[str, None] = '20261029_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'ai_analyses' not in existing_tables:
        op.create_table(
            'ai_analyses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('issue_id', sa.Integer(), nullable=False),
            sa.Column('model_name', sa.String(length=100), nullable=False, server_default='CivicYOLO-v8'),
            sa.Column('model_version', sa.String(length=50), nullable=False, server_default='1.0.0'),
            sa.Column('predicted_category', sa.String(length=100), nullable=True),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('detected_objects', sa.JSON(), nullable=True),
            sa.Column('suggested_severity', sa.String(length=50), nullable=True),
            sa.Column('suggested_priority', sa.String(length=50), nullable=True),
            sa.Column('suggested_department_id', sa.Integer(), nullable=True),
            sa.Column('explanation', sa.Text(), nullable=True),
            sa.Column('annotated_image_path', sa.String(length=500), nullable=True),
            sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='PENDING'),
            sa.Column('review_status', sa.String(length=50), nullable=False, server_default='PENDING'),
            sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('review_comment', sa.Text(), nullable=True),
            sa.Column('analysis_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['issue_id'], ['civic_issues.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['suggested_department_id'], ['departments.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_ai_analyses_id', 'ai_analyses', ['id'], unique=False)
        op.create_index('ix_ai_analyses_issue_id', 'ai_analyses', ['issue_id'], unique=False)
        op.create_index('ix_ai_analyses_predicted_category', 'ai_analyses', ['predicted_category'], unique=False)
        op.create_index('ix_ai_analyses_suggested_department_id', 'ai_analyses', ['suggested_department_id'], unique=False)
        op.create_index('ix_ai_analyses_processing_status', 'ai_analyses', ['processing_status'], unique=False)
        op.create_index('ix_ai_analyses_review_status', 'ai_analyses', ['review_status'], unique=False)
        op.create_index('ix_ai_analyses_created_at', 'ai_analyses', ['created_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'ai_analyses' in existing_tables:
        op.drop_index('ix_ai_analyses_created_at', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_review_status', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_processing_status', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_suggested_department_id', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_predicted_category', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_issue_id', table_name='ai_analyses')
        op.drop_index('ix_ai_analyses_id', table_name='ai_analyses')
        op.drop_table('ai_analyses')

