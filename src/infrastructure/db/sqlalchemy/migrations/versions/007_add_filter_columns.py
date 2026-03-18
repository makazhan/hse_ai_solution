"""Добавление 4 текстовых колонок для фильтров (work_type, equipment,
safety_responsible_person, weather_conditions)

Revision ID: 007_add_filter_columns
Revises: 006_drop_chat_tables
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa


revision = '007_add_filter_columns'
down_revision = '006_drop_chat_tables'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incidents', sa.Column('work_type', sa.String(500), nullable=True))
    op.add_column('incidents', sa.Column('equipment', sa.String(500), nullable=True))
    op.add_column('incidents', sa.Column('safety_responsible_person', sa.String(500), nullable=True))
    op.add_column('incidents', sa.Column('weather_conditions', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('incidents', 'weather_conditions')
    op.drop_column('incidents', 'safety_responsible_person')
    op.drop_column('incidents', 'equipment')
    op.drop_column('incidents', 'work_type')
