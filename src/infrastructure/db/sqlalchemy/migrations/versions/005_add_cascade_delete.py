"""Add cascade delete to chat foreign keys

Revision ID: 005_add_cascade_delete
Revises: 004_enum_to_varchar
Create Date: 2026-01-26 15:00:00.000000

NOTE: Изменяла FK чат-таблиц из 001_c9e79a48, которые удалены
в 006_drop_chat_tables. Миграция оставлена как no-op для сохранения цепочки.
"""

revision = '005_add_cascade_delete'
down_revision = '004_enum_to_varchar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
