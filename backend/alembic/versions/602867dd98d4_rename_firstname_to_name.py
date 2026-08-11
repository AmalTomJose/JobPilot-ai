"""rename firstname to name

Revision ID: 602867dd98d4
Revises: 9b5bb8692d67
Create Date: 2026-08-11 23:26:29.318258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '602867dd98d4'
down_revision: Union[str, Sequence[str], None] = '9b5bb8692d67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "firstname",
        new_column_name="name",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "name",
        new_column_name="firstname",
    )