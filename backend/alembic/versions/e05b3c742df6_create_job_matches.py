"""Persist explainable skill matching snapshots.

Revision ID: e05b3c742df6
Revises: d94a2b631ce5
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e05b3c742df6'
down_revision = 'd94a2b631ce5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('job_matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('profile_revision', sa.Integer(), nullable=False),
        sa.Column('job_revision', sa.Integer(), nullable=False),
        sa.Column('matcher_version', sa.String(40), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('matched_skills', postgresql.JSONB(), nullable=False),
        sa.Column('missing_skills', postgresql.JSONB(), nullable=False),
        sa.Column('reason', sa.String(40), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('job_id', name='uq_job_matches_job'),
        sa.CheckConstraint('score IS NULL OR (score >= 0 AND score <= 100)', name='ck_job_matches_score'),
        sa.CheckConstraint('profile_revision >= 1 AND job_revision >= 1', name='ck_job_matches_revisions'))


def downgrade():
    op.drop_table('job_matches')
