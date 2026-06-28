"""Add mcp_status, mcp_error, last_checked columns to mcp_plugins.

Revision ID: 20260628_0001
Revises: 6b215033abad
Create Date: 2026-06-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260628_0001'
down_revision: Union[str, None] = '6b215033abad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mcp_plugins',
        sa.Column('mcp_status', sa.String(length=50), nullable=False,
                  server_default='active'))
    op.add_column('mcp_plugins',
        sa.Column('mcp_error', sa.Text(), nullable=True))
    op.add_column('mcp_plugins',
        sa.Column('last_checked', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('mcp_plugins', 'last_checked')
    op.drop_column('mcp_plugins', 'mcp_error')
    op.drop_column('mcp_plugins', 'mcp_status')
