"""Add missing columns: careers.career_type, organizations.alignment,
outlines.target_words, plot_analyses.chapter_index,
story_memories.chapter_index, story_memories.memory_layer.

Revision ID: 20260628_0002
Revises: 20260628_0001
Create Date: 2026-06-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260628_0002'
down_revision: Union[str, None] = '20260628_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # careers — missing career_type
    op.add_column('careers',
        sa.Column('career_type', sa.String(length=100), nullable=False,
                  server_default='主要职业'))

    # organizations — missing alignment
    op.add_column('organizations',
        sa.Column('alignment', sa.String(length=20), nullable=False,
                  server_default='中立'))

    # outlines — missing target_words
    op.add_column('outlines',
        sa.Column('target_words', sa.Integer(), nullable=False,
                  server_default='3000'))

    # plot_analyses — missing chapter_index
    op.add_column('plot_analyses',
        sa.Column('chapter_index', sa.Integer(), nullable=False,
                  server_default='0'))

    # story_memories — missing chapter_index and memory_layer
    op.add_column('story_memories',
        sa.Column('chapter_index', sa.Integer(), nullable=False,
                  server_default='0'))
    op.add_column('story_memories',
        sa.Column('memory_layer', sa.String(length=20), nullable=False,
                  server_default='short_term'))


def downgrade() -> None:
    op.drop_column('story_memories', 'memory_layer')
    op.drop_column('story_memories', 'chapter_index')
    op.drop_column('plot_analyses', 'chapter_index')
    op.drop_column('outlines', 'target_words')
    op.drop_column('organizations', 'alignment')
    op.drop_column('careers', 'career_type')
