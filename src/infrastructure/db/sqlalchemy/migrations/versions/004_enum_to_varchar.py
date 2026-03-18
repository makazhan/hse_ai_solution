"""Change enums to varchar

Revision ID: 004_enum_to_varchar
Revises: 003_change_embedding_dimension
Create Date: 2026-01-26 12:00:00.000000

NOTE: Изменяла enum-колонки NPA-таблиц из 002_npa_schema, которая теперь no-op.
Миграция оставлена как no-op для сохранения цепочки.
"""

revision = '004_enum_to_varchar'
down_revision = '003_change_embedding_dimension'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
