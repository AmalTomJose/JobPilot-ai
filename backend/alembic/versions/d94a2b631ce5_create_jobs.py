"""Add immutable email imports and reviewed jobs.

Revision ID: d94a2b631ce5
Revises: c83f1a520bd4
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'd94a2b631ce5'
down_revision = 'c83f1a520bd4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('job_imports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('parser_version', sa.String(40), nullable=False),
        sa.Column('draft_data', postgresql.JSONB(), nullable=False),
        sa.Column('warnings', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_job_imports_user'),
        sa.UniqueConstraint('user_id', 'source_hash', name='uq_job_imports_user_hash'))
    op.create_table('jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_import_id', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.String(10), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('work_mode', sa.String(10), nullable=True),
        sa.Column('employment_type', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSONB(), nullable=False),
        sa.Column('application_url', sa.Text(), nullable=True),
        sa.Column('url_hash', sa.String(64), nullable=True),
        sa.Column('status', sa.String(10), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_jobs_user'),
        sa.ForeignKeyConstraint(['source_import_id'], ['job_imports.id'], ondelete='SET NULL', name='fk_jobs_import'),
        sa.UniqueConstraint('user_id', 'url_hash', name='uq_jobs_user_url'),
        sa.UniqueConstraint('source_import_id', name='uq_jobs_import'),
        sa.CheckConstraint("status IN ('saved', 'archived')", name='ck_jobs_status'),
        sa.CheckConstraint("source_type IN ('manual', 'email')", name='ck_jobs_source'),
        sa.CheckConstraint("work_mode IS NULL OR work_mode IN ('remote', 'hybrid', 'onsite')", name='ck_jobs_work_mode'),
        sa.CheckConstraint('revision >= 1', name='ck_jobs_revision'))
    op.create_index('ix_jobs_user_created', 'jobs', ['user_id', 'created_at', 'id'])


def downgrade():
    op.drop_index('ix_jobs_user_created', table_name='jobs')
    op.drop_table('jobs')
    op.drop_table('job_imports')
