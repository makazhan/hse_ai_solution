"""Добавление колонок victim_count, fatality_count, safety_training_completed,
is_recurrent, regulatory_compliant + миграция данных fatality_count

Revision ID: 008_count_training_cols
Revises: 007_add_filter_columns
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa


revision = '008_count_training_cols'
down_revision = '007_add_filter_columns'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incidents', sa.Column('victim_count', sa.SmallInteger(), nullable=False, server_default='1'))
    op.add_column('incidents', sa.Column('fatality_count', sa.SmallInteger(), nullable=False, server_default='0'))
    op.add_column('incidents', sa.Column('safety_training_completed', sa.Boolean(), nullable=True))
    op.add_column('incidents', sa.Column('is_recurrent', sa.Boolean(), nullable=True))
    op.add_column('incidents', sa.Column('regulatory_compliant', sa.Boolean(), nullable=True))
    # Миграция данных: fatality_count = 1 для существующих записей со смертельным исходом
    op.execute("UPDATE incidents SET fatality_count = 1 WHERE injury_type = 'Смертельный исход'")


def downgrade():
    op.drop_column('incidents', 'regulatory_compliant')
    op.drop_column('incidents', 'is_recurrent')
    op.drop_column('incidents', 'safety_training_completed')
    op.drop_column('incidents', 'fatality_count')
    op.drop_column('incidents', 'victim_count')
