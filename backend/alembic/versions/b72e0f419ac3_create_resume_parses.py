"""Store the current structured draft for each resume.

Revision ID: b72e0f419ac3
Revises: 767a67c5e23e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b72e0f419ac3'
down_revision = '767a67c5e23e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'resume_parses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('parser_version', sa.String(40), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('draft_data', postgresql.JSONB(), nullable=True),
        sa.Column('warnings', postgresql.JSONB(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE', name='fk_resume_parses_resume_id'),
        sa.UniqueConstraint('resume_id', name='uq_resume_parses_resume_id'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_resume_parses_status'),
    )


def downgrade():
    op.drop_table('resume_parses')
