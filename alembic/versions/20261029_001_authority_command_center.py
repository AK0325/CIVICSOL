"""Authority Command Center schema migration

Revision ID: 20261029_001
Revises: None
Create Date: 2026-10-29 20:45:00.000000

Schema extensions:
1. Create 'departments' table.
2. Extend 'users' table with role, department_id, designation, employee_id, is_active.
3. Extend 'civic_issues' table with assignment, department_id, and resolution fields.
4. Create 'issue_status_history' table.
5. Create 'audit_logs' table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261029_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------
    # 1. CREATE DEPARTMENTS TABLE
    # -----------------------------------------------------
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)

    # -----------------------------------------------------
    # 2. EXTEND USERS TABLE
    # -----------------------------------------------------
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=30), server_default='CITIZEN', nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('department_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('designation', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('employee_id', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )

    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_department_id'), 'users', ['department_id'], unique=False)
    op.create_index(op.f('ix_users_employee_id'), 'users', ['employee_id'], unique=True)
    op.create_foreign_key(
        'fk_users_department_id_departments',
        'users',
        'departments',
        ['department_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # -----------------------------------------------------
    # 3. EXTEND CIVIC_ISSUES TABLE
    # -----------------------------------------------------
    op.add_column(
        'civic_issues',
        sa.Column('department_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('assigned_officer_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('resolution_notes', sa.Text(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('resolution_image_path', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'civic_issues',
        sa.Column('rejection_reason', sa.Text(), nullable=True),
    )

    op.create_index(op.f('ix_civic_issues_department_id'), 'civic_issues', ['department_id'], unique=False)
    op.create_index(op.f('ix_civic_issues_assigned_officer_id'), 'civic_issues', ['assigned_officer_id'], unique=False)

    op.create_foreign_key(
        'fk_civic_issues_department_id_departments',
        'civic_issues',
        'departments',
        ['department_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_civic_issues_assigned_officer_id_users',
        'civic_issues',
        'users',
        ['assigned_officer_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_civic_issues_assigned_by_id_users',
        'civic_issues',
        'users',
        ['assigned_by_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_civic_issues_resolved_by_id_users',
        'civic_issues',
        'users',
        ['resolved_by_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # -----------------------------------------------------
    # 4. CREATE ISSUE_STATUS_HISTORY TABLE
    # -----------------------------------------------------
    op.create_table(
        'issue_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['issue_id'], ['civic_issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_issue_status_history_id'), 'issue_status_history', ['id'], unique=False)
    op.create_index(op.f('ix_issue_status_history_issue_id'), 'issue_status_history', ['issue_id'], unique=False)
    op.create_index(op.f('ix_issue_status_history_to_status'), 'issue_status_history', ['to_status'], unique=False)
    op.create_index(op.f('ix_issue_status_history_created_at'), 'issue_status_history', ['created_at'], unique=False)

    # -----------------------------------------------------
    # 5. CREATE AUDIT_LOGS TABLE
    # -----------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    # 1. Drop audit logs
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    # 2. Drop issue status history
    op.drop_index(op.f('ix_issue_status_history_created_at'), table_name='issue_status_history')
    op.drop_index(op.f('ix_issue_status_history_to_status'), table_name='issue_status_history')
    op.drop_index(op.f('ix_issue_status_history_issue_id'), table_name='issue_status_history')
    op.drop_index(op.f('ix_issue_status_history_id'), table_name='issue_status_history')
    op.drop_table('issue_status_history')

    # 3. Drop civic_issues extensions
    op.drop_constraint('fk_civic_issues_resolved_by_id_users', 'civic_issues', type_='foreignkey')
    op.drop_constraint('fk_civic_issues_assigned_by_id_users', 'civic_issues', type_='foreignkey')
    op.drop_constraint('fk_civic_issues_assigned_officer_id_users', 'civic_issues', type_='foreignkey')
    op.drop_constraint('fk_civic_issues_department_id_departments', 'civic_issues', type_='foreignkey')
    op.drop_index(op.f('ix_civic_issues_assigned_officer_id'), table_name='civic_issues')
    op.drop_index(op.f('ix_civic_issues_department_id'), table_name='civic_issues')

    op.drop_column('civic_issues', 'rejection_reason')
    op.drop_column('civic_issues', 'resolved_at')
    op.drop_column('civic_issues', 'resolved_by_id')
    op.drop_column('civic_issues', 'resolution_image_path')
    op.drop_column('civic_issues', 'resolution_notes')
    op.drop_column('civic_issues', 'assigned_at')
    op.drop_column('civic_issues', 'assigned_by_id')
    op.drop_column('civic_issues', 'assigned_officer_id')
    op.drop_column('civic_issues', 'department_id')

    # 4. Drop users extensions
    op.drop_constraint('fk_users_department_id_departments', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_employee_id'), table_name='users')
    op.drop_index(op.f('ix_users_department_id'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')

    op.drop_column('users', 'is_active')
    op.drop_column('users', 'employee_id')
    op.drop_column('users', 'designation')
    op.drop_column('users', 'department_id')
    op.drop_column('users', 'role')

    # 5. Drop departments table
    op.drop_index(op.f('ix_departments_code'), table_name='departments')
    op.drop_index(op.f('ix_departments_name'), table_name='departments')
    op.drop_index(op.f('ix_departments_id'), table_name='departments')
    op.drop_table('departments')
