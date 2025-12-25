"""set default driver role

Revision ID: 5067e470998b
Revises: 9748efda9e76
Create Date: 2025-12-25 13:19:45.862220
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5067e470998b'
down_revision = '9748efda9e76'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # PostgreSQL supports altering defaults
        op.alter_column(
            "users",
            "role",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default="driver"
        )

    # Always fix existing rows regardless of dialect
    op.execute("UPDATE users SET role='driver' WHERE role='receiver'")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Revert default back to 'receiver' in Postgres
        op.alter_column(
            "users",
            "role",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default="receiver"
        )

    # Optional rollback of data
    op.execute("UPDATE users SET role='receiver' WHERE role='driver'")