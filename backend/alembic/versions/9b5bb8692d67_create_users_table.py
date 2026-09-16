"""create users table

Revision ID: 9b5bb8692d67
Revises: 3af135758130
Create Date: 2026-08-11 22:44:33.592171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b5bb8692d67'
down_revision: Union[str, Sequence[str], None] = '3af135758130'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve existing password values and backfill timestamps for older rows.

    The legacy password column is expected to contain hashes. This migration
    deliberately preserves its contents rather than guessing a password format.
    See README for the legacy-password audit required before upgrading old data.
    """
    op.alter_column('users', 'password', new_column_name='password_hash')
    op.add_column('users', sa.Column(
        'created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()
    ))
    op.alter_column('users', 'created_at', server_default=None)


def downgrade() -> None:
    # Renaming preserves credential data in both directions.
    op.alter_column('users', 'password_hash', new_column_name='password')
    op.drop_column('users', 'created_at')
