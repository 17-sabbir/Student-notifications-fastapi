"""make_device_id_non_nullable

Revision ID: 2620bbc51cd3
Revises: 10315a8df56d
Create Date: 2026-08-27 02:19:44.261158
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid


revision: str = '2620bbc51cd3'
down_revision: Union[str, None] = '10315a8df56d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    devices = connection.execute(sa.text("SELECT id FROM device_tokens WHERE device_id IS NULL")).fetchall()
    for row in devices:
        connection.execute(
            sa.text("UPDATE device_tokens SET device_id = :device_id WHERE id = :id"),
            {"device_id": str(uuid.uuid4()), "id": row[0]},
        )
    op.alter_column('device_tokens', 'device_id', existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.alter_column('device_tokens', 'device_id', existing_type=sa.String(length=255), nullable=True)
