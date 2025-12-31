"""V2 schema: add validated field to findings, report_jobs, audit_bundle_jobs, integration_configs

Revision ID: 83beebbd6e79
Revises: 2b765485f3ec
Create Date: 2025-12-26 15:13:32.366523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '83beebbd6e79'
down_revision: Union[str, None] = '2b765485f3ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add validation fields to findings table
    op.add_column('findings', sa.Column('validated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('findings', sa.Column('validator_id', UUID(as_uuid=True), nullable=True))
    op.add_column('findings', sa.Column('validated_at', sa.TIMESTAMP(timezone=True), nullable=True))

    op.create_index('ix_findings_validated', 'findings', ['validated'])
    op.create_index('ix_findings_validated_at', 'findings', ['validated_at'])

    # Create report_jobs table
    op.create_table(
        'report_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('format', sa.Enum('HTML', 'PDF', name='reportformat'), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='jobstatus'), nullable=False, server_default='QUEUED'),
        sa.Column('artifact_uri', sa.String(500), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index('ix_report_jobs_run_id', 'report_jobs', ['run_id'])
    op.create_index('ix_report_jobs_status', 'report_jobs', ['status'])
    op.create_foreign_key('fk_report_jobs_run_id', 'report_jobs', 'runs', ['run_id'], ['id'], ondelete='CASCADE')

    # Create audit_bundle_jobs table
    op.create_table(
        'audit_bundle_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='jobstatus'), nullable=False, server_default='QUEUED'),
        sa.Column('artifact_uri', sa.String(500), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index('ix_audit_bundle_jobs_run_id', 'audit_bundle_jobs', ['run_id'])
    op.create_index('ix_audit_bundle_jobs_status', 'audit_bundle_jobs', ['status'])
    op.create_foreign_key('fk_audit_bundle_jobs_run_id', 'audit_bundle_jobs', 'runs', ['run_id'], ['id'], ondelete='CASCADE')

    # Create integration_configs table
    op.create_table(
        'integration_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.Enum('SLACK', 'JIRA', 'WEBHOOK', name='integrationtype'), nullable=False),
        sa.Column('config', JSONB, nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_integration_configs_type', 'integration_configs', ['type'])


def downgrade() -> None:
    # Drop integration_configs table
    op.drop_index('ix_integration_configs_type', 'integration_configs')
    op.drop_table('integration_configs')

    # Drop audit_bundle_jobs table
    op.drop_constraint('fk_audit_bundle_jobs_run_id', 'audit_bundle_jobs', type_='foreignkey')
    op.drop_index('ix_audit_bundle_jobs_status', 'audit_bundle_jobs')
    op.drop_index('ix_audit_bundle_jobs_run_id', 'audit_bundle_jobs')
    op.drop_table('audit_bundle_jobs')

    # Drop report_jobs table
    op.drop_constraint('fk_report_jobs_run_id', 'report_jobs', type_='foreignkey')
    op.drop_index('ix_report_jobs_status', 'report_jobs')
    op.drop_index('ix_report_jobs_run_id', 'report_jobs')
    op.drop_table('report_jobs')

    # Drop enums (shared by both tables)
    sa.Enum(name='jobstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reportformat').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='integrationtype').drop(op.get_bind(), checkfirst=True)

    # Remove validation fields from findings table
    op.drop_index('ix_findings_validated_at', 'findings')
    op.drop_index('ix_findings_validated', 'findings')
    op.drop_column('findings', 'validated_at')
    op.drop_column('findings', 'validator_id')
    op.drop_column('findings', 'validated')
