"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00

"""
from __future__ import annotations

from alembic import op

from app.db import models  # noqa: F401
from app.db.base import Base


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
