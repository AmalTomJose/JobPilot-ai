"""Store one independently confirmed profile per user.

Revision ID: c83f1a520bd4
Revises: b72e0f419ac3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c83f1a520bd4'
down_revision = 'b72e0f419ac3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_resume_id', sa.Integer(), nullable=True),
        sa.Column('source_parser_version', sa.String(40), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_profiles_user_id'),
        sa.ForeignKeyConstraint(['source_resume_id'], ['resumes.id'], ondelete='SET NULL', name='fk_profiles_source_resume_id'),
        sa.UniqueConstraint('user_id', name='uq_profiles_user_id'),
        sa.CheckConstraint('revision >= 1', name='ck_profiles_revision'),
    )


def downgrade():
    op.drop_table('profiles')
