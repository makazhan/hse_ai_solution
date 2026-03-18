"""NPA schema for Kazakhstan legal acts RAG system

Revision ID: 002_npa_schema
Revises: 001_c9e79a48
Create Date: 2026-01-25 12:00:00.000000

NOTE: Нормализованная 8-табличная NPA-схема заменена на плоские chunk-таблицы
в 009_npa_flat_schema (см. docs/plan-rag.md). Миграция оставлена как no-op
для сохранения цепочки.
"""
# revision identifiers, used by Alembic.
revision = '002_npa_schema'
down_revision = '001_c9e79a48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
