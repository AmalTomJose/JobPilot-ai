"""Separate automatically discovered openings from approved jobs and drafts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'b38e6fa750c9'
down_revision = 'a27d5e964fb8'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('discovered_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_message_id', sa.Integer(), sa.ForeignKey('email_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('identity_hash', sa.String(64), nullable=False),
        sa.Column('job_url', sa.String(2048)),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='SET NULL')),
        sa.Column('draft_data', postgresql.JSONB(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('warnings', postgresql.JSONB(), nullable=False),
        sa.Column('parser_version', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'identity_hash', name='uq_discovered_owner_identity'),
        sa.CheckConstraint("status IN ('pending', 'dismissed', 'approved')", name='ck_discovered_status'))
    op.create_index('ix_discovered_owner_status', 'discovered_jobs', ['user_id', 'status', 'id'])

def downgrade():
    op.drop_table('discovered_jobs')
