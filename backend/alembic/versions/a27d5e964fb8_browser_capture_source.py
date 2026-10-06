"""Track explicitly saved browser imports; previews have no database table."""
from alembic import op
import sqlalchemy as sa

revision = 'a27d5e964fb8'
down_revision = 'f16c4d853ea7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job_imports', sa.Column('source_type', sa.String(10), nullable=False, server_default='email'))
    op.alter_column('job_imports', 'source_type', server_default=None)
    op.drop_constraint('ck_jobs_source', 'jobs', type_='check')
    op.create_check_constraint('ck_jobs_source', 'jobs', "source_type IN ('manual', 'email', 'browser')")


def downgrade():
    # Preserve jobs when returning to a schema without browser provenance.
    op.execute("UPDATE jobs SET source_type = CASE WHEN source_import_id IS NULL THEN 'manual' ELSE 'email' END WHERE source_type = 'browser'")
    op.drop_constraint('ck_jobs_source', 'jobs', type_='check')
    op.create_check_constraint('ck_jobs_source', 'jobs', "source_type IN ('manual', 'email')")
    op.drop_column('job_imports', 'source_type')
