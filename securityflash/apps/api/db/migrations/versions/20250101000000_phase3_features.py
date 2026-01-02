"""Phase 3 features: validation packs, monitored mode, swarm, model router.

Revision ID: 20250101000000
Revises: 28426e2cd3da
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250101000000'
down_revision = '28426e2cd3da'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend run status enum
    op.execute("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'ABORTED'")

    # Runs: monitored mode / kill switch
    op.add_column('runs', sa.Column('monitored_mode_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('runs', sa.Column('kill_switch_armed', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('runs', sa.Column('kill_switch_activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('runs', sa.Column('monitored_rate_limit_rpm', sa.Integer(), nullable=False, server_default='60'))
    op.add_column('runs', sa.Column('monitored_max_concurrency', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('runs', sa.Column('monitored_started_by', sa.String(length=255), nullable=True))

    # LLM calls: provider routing
    op.add_column('llm_calls', sa.Column('provider', sa.String(length=100), nullable=False, server_default='openai'))
    op.add_column('llm_calls', sa.Column('role', sa.String(length=50), nullable=False, server_default='PLANNER'))
    op.add_column('llm_calls', sa.Column('tokens_est', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('llm_calls', sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'))

    # Validation packs table
    risk_enum = postgresql.ENUM('LOW', 'MED', 'HIGH', name='validationrisklevel')
    status_enum = postgresql.ENUM('DRAFT', 'READY', 'IN_PROGRESS', 'COMPLETE', 'ABORTED', name='validationstatus')
    risk_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'validation_packs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('scope_id', sa.UUID(), nullable=False),
        sa.Column('finding_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('risk_level', risk_enum, nullable=False),
        sa.Column('instructions_md', sa.Text(), nullable=False),
        sa.Column('command_templates', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('stop_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('required_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('status', status_enum, nullable=False, server_default='DRAFT'),
        sa.Column('approved_by_reviewer', sa.String(length=255), nullable=True),
        sa.Column('approved_by_engineer', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('abort_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_validation_packs_finding_id_findings'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_validation_packs_project_id_projects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_validation_packs_run_id_runs'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scope_id'], ['scopes.id'], name=op.f('fk_validation_packs_scope_id_scopes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_validation_packs'))
    )
    op.create_index(op.f('ix_validation_packs_finding_id'), 'validation_packs', ['finding_id'], unique=False)
    op.create_index(op.f('ix_validation_packs_project_id'), 'validation_packs', ['project_id'], unique=False)
    op.create_index(op.f('ix_validation_packs_run_id'), 'validation_packs', ['run_id'], unique=False)
    op.create_index(op.f('ix_validation_packs_scope_id'), 'validation_packs', ['scope_id'], unique=False)
    op.create_index(op.f('ix_validation_packs_status'), 'validation_packs', ['status'], unique=False)

    # Evidence association
    op.add_column('evidence', sa.Column('validation_pack_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_evidence_validation_pack_id'), 'evidence', ['validation_pack_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_evidence_validation_pack_id_validation_packs'),
        'evidence',
        'validation_packs',
        ['validation_pack_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Swarm models
    task_enum = postgresql.ENUM('RECON', 'ENUM', 'ANALYZE', 'VALIDATE', 'WRITE_PACK', name='swarmtasktype')
    task_status_enum = postgresql.ENUM('QUEUED', 'RUNNING', 'DONE', 'FAILED', 'CANCELLED', name='swarmtaskstatus')
    task_enum.create(op.get_bind(), checkfirst=True)
    task_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'swarm_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('task_type', task_enum, nullable=False),
        sa.Column('target_key', sa.String(length=255), nullable=False),
        sa.Column('objective', sa.String(length=2000), nullable=False),
        sa.Column('status', task_status_enum, nullable=False, server_default='QUEUED'),
        sa.Column('assigned_agent_id', sa.String(length=255), nullable=True),
        sa.Column('dedupe_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_swarm_tasks_run_id_runs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_swarm_tasks')),
        sa.UniqueConstraint('run_id', 'dedupe_key', name='uq_swarm_task_dedupe')
    )
    op.create_index(op.f('ix_swarm_tasks_run_id'), 'swarm_tasks', ['run_id'], unique=False)
    op.create_index(op.f('ix_swarm_tasks_status'), 'swarm_tasks', ['status'], unique=False)

    op.create_table(
        'swarm_locks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('lock_key', sa.String(length=255), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('owner_agent_id', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_swarm_locks_run_id_runs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_swarm_locks')),
        sa.UniqueConstraint('lock_key', name='uq_swarm_lock_key')
    )
    op.create_index(op.f('ix_swarm_locks_run_id'), 'swarm_locks', ['run_id'], unique=False)

    op.create_table(
        'swarm_budgets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('max_tasks_total', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('max_tasks_running', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('max_requests_total', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('max_requests_per_minute', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('tokens_budget', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_swarm_budgets_run_id_runs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_swarm_budgets'))
    )
    op.create_index(op.f('ix_swarm_budgets_run_id'), 'swarm_budgets', ['run_id'], unique=True)


def downgrade() -> None:
    # Swarm tables
    op.drop_index(op.f('ix_swarm_budgets_run_id'), table_name='swarm_budgets')
    op.drop_table('swarm_budgets')

    op.drop_index(op.f('ix_swarm_locks_run_id'), table_name='swarm_locks')
    op.drop_table('swarm_locks')

    op.drop_index(op.f('ix_swarm_tasks_status'), table_name='swarm_tasks')
    op.drop_index(op.f('ix_swarm_tasks_run_id'), table_name='swarm_tasks')
    op.drop_table('swarm_tasks')
    op.execute("DROP TYPE IF EXISTS swarmtaskstatus")
    op.execute("DROP TYPE IF EXISTS swarmtasktype")

    # Evidence association
    op.drop_constraint(op.f('fk_evidence_validation_pack_id_validation_packs'), 'evidence', type_='foreignkey')
    op.drop_index(op.f('ix_evidence_validation_pack_id'), table_name='evidence')
    op.drop_column('evidence', 'validation_pack_id')

    # Validation packs
    op.drop_index(op.f('ix_validation_packs_status'), table_name='validation_packs')
    op.drop_index(op.f('ix_validation_packs_scope_id'), table_name='validation_packs')
    op.drop_index(op.f('ix_validation_packs_run_id'), table_name='validation_packs')
    op.drop_index(op.f('ix_validation_packs_project_id'), table_name='validation_packs')
    op.drop_index(op.f('ix_validation_packs_finding_id'), table_name='validation_packs')
    op.drop_table('validation_packs')
    op.execute("DROP TYPE IF EXISTS validationstatus")
    op.execute("DROP TYPE IF EXISTS validationrisklevel")

    # LLM columns
    op.drop_column('llm_calls', 'latency_ms')
    op.drop_column('llm_calls', 'tokens_est')
    op.drop_column('llm_calls', 'role')
    op.drop_column('llm_calls', 'provider')

    # Run columns
    op.drop_column('runs', 'monitored_started_by')
    op.drop_column('runs', 'monitored_max_concurrency')
    op.drop_column('runs', 'monitored_rate_limit_rpm')
    op.drop_column('runs', 'kill_switch_activated_at')
    op.drop_column('runs', 'kill_switch_armed')
    op.drop_column('runs', 'monitored_mode_enabled')
    # Note: runstatus enum retains ABORTED value for safety
