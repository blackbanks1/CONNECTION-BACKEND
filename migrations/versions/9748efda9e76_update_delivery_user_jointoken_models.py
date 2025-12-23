"""Update Delivery, User, JoinToken models

Revision ID: 9748efda9e76
Revises: 9065ef9fc5e1
Create Date: 2025-12-23 18:26:52.283525

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9748efda9e76'
down_revision = '9065ef9fc5e1'
branch_labels = None
depends_on = None


def upgrade():
    # --- Delivery model changes ---
    # No changes needed; receiver_phone already removed in DB

    # --- User model changes ---
    # Columns already exist in DB, so skip adding them

    # --- JoinToken model changes ---
    with op.batch_alter_table('join_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('delivery_id', sa.Integer(), nullable=False))
        batch_op.alter_column(
            'email',
            existing_type=sa.VARCHAR(length=120),
            nullable=True
        )
        batch_op.create_foreign_key(
            'fk_join_tokens_delivery_id',
            'deliveries',
            ['delivery_id'],
            ['id']
        )


def downgrade():
    # --- JoinToken rollback ---
    with op.batch_alter_table('join_tokens', schema=None) as batch_op:
        batch_op.drop_constraint('fk_join_tokens_delivery_id', type_='foreignkey')
        batch_op.alter_column(
            'email',
            existing_type=sa.VARCHAR(length=120),
            nullable=False
        )
        batch_op.drop_column('delivery_id')

    # --- User rollback ---
    # Skip dropping columns since we didn’t add them in upgrade

    # --- Delivery rollback ---
    # Skip re-adding receiver_phone since it was never dropped here