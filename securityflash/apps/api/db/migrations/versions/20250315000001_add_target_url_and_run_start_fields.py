"""Add target_url to projects and approvals to runs"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250315000001"
down_revision = "20250101000000_phase3_features"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("target_url", sa.String(length=500), nullable=True))
    op.add_column("projects", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("runs", sa.Column("reviewer_approval", sa.String(length=255), nullable=True))
    op.add_column("runs", sa.Column("engineer_approval", sa.String(length=255), nullable=True))
    op.add_column("runs", sa.Column("started_by", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("runs", "started_by")
    op.drop_column("runs", "engineer_approval")
    op.drop_column("runs", "reviewer_approval")
    op.drop_column("projects", "deleted_at")
    op.drop_column("projects", "target_url")
