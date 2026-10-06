"""Gmail connection, original messages, and sync runs.
Revision ID: f16c4d853ea7
Revises: e05b3c742df6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'f16c4d853ea7'
down_revision = 'e05b3c742df6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('mailbox_email', sa.String(320)),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text()),
        sa.Column('state_hash', sa.String(64), unique=True),
        sa.Column('browser_hash', sa.String(64)),
        sa.Column('state_expires_at', sa.DateTime()),
        sa.Column('verifier_encrypted', sa.Text()),
        sa.Column('label_id', sa.String(255)),
        sa.Column('label_name', sa.String(255)),
        sa.Column('import_since', sa.DateTime()),
        sa.Column('auto_sync', sa.Boolean(), nullable=False),
        sa.Column('next_sync_at', sa.DateTime()),
        sa.Column('last_sync_at', sa.DateTime()),
        sa.Column('last_error', sa.String(500)),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('scan_before', sa.Integer()),
        sa.Column('page_token', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_table('email_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_email', sa.String(320), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=False),
        sa.Column('subject', sa.Text(), nullable=False),
        sa.Column('sender', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime()),
        sa.Column('payload_data', postgresql.JSONB(), nullable=False),
        sa.Column('raw_text', sa.Text()),
        sa.Column('import_id', sa.Integer(), sa.ForeignKey('job_imports.id', ondelete='SET NULL')),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('warning', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'mailbox_email', 'provider_message_id', name='uq_email_message_owner_mailbox'))
    op.create_index('ix_email_messages_owner_id', 'email_messages', ['user_id', 'id'])
    op.create_table('email_sync_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('imported', sa.Integer(), nullable=False),
        sa.Column('skipped', sa.Integer(), nullable=False),
        sa.Column('needs_review', sa.Integer(), nullable=False),
        sa.Column('error', sa.String(500)))
    op.create_index('ix_email_sync_runs_owner_id', 'email_sync_runs', ['user_id', 'id'])


def downgrade():
    op.drop_index('ix_email_sync_runs_owner_id', table_name='email_sync_runs')
    op.drop_table('email_sync_runs')
    op.drop_index('ix_email_messages_owner_id', table_name='email_messages')
    op.drop_table('email_messages')
    op.drop_table('email_connections')
