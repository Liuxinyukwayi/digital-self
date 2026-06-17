"""v2 memory expansion

Revision ID: 002
Revises: 001
Create Date: 2026-06-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('memories', sa.Column('evidence_count', sa.Integer(), server_default='1', nullable=True))
    op.add_column('memories', sa.Column('confidence', sa.Float(), server_default='0.5', nullable=True))
    op.add_column('memories', sa.Column('last_evidence_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'persona_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('values', sa.JSON(), nullable=True),
        sa.Column('goals', sa.JSON(), nullable=True),
        sa.Column('speech_style', sa.JSON(), nullable=True),
        sa.Column('thinking_style', sa.String(length=200), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_persona_profiles_id'), 'persona_profiles', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_persona_profiles_id'), table_name='persona_profiles')
    op.drop_table('persona_profiles')
    op.drop_column('memories', 'last_evidence_at')
    op.drop_column('memories', 'confidence')
    op.drop_column('memories', 'evidence_count')
