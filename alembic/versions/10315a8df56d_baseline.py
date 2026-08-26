"""baseline

Revision ID: 10315a8df56d
Revises: 
Create Date: 2026-08-27 02:19:10.972446
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '10315a8df56d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('device_tokens', sa.Column('device_id', sa.String(length=255), nullable=True))
    op.add_column('device_tokens', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('device_tokens', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('device_tokens', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_device_tokens_device_id'), 'device_tokens', ['device_id'], unique=True)
    op.create_index(op.f('ix_device_tokens_fcm_token'), 'device_tokens', ['fcm_token'], unique=True)
    op.create_index(op.f('ix_device_tokens_user_id'), 'device_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_device_tokens_user_id'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_fcm_token'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_device_id'), table_name='device_tokens')
    op.drop_column('device_tokens', 'last_seen_at')
    op.drop_column('device_tokens', 'updated_at')
    op.drop_column('device_tokens', 'is_active')
    op.drop_column('device_tokens', 'device_id')
