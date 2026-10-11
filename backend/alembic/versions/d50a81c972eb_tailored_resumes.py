"""Store separate, reviewed resume versions for saved jobs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'd50a81c972eb'
down_revision = 'c49f70b861da'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tailored_resumes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('profile_revision', sa.Integer(), nullable=False),
        sa.Column('job_revision', sa.Integer(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('profile_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('job_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('proposal', postgresql.JSONB(), nullable=True),
        sa.Column('section_order', postgresql.JSONB(), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('prompt_version', sa.String(40), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('user_id', 'request_id', name='uq_tailoring_request'),
        sa.CheckConstraint("status IN ('generating','draft','approved','failed')", name='ck_tailoring_status'),
        sa.CheckConstraint('revision >= 1 AND profile_revision >= 1 AND job_revision >= 1', name='ck_tailoring_revisions'))
    op.create_index('ix_tailoring_owner_job', 'tailored_resumes', ['user_id','job_id','id'])

def downgrade():
    op.drop_table('tailored_resumes')
