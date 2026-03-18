"""empty message

Revision ID: 001_c9e79a48
Revises:
Create Date: 2026-01-22 12:03:56.272329

NOTE: Таблицы чата (chats, user_messages, agent_responses) удалены
в 006_drop_chat_tables. Миграция оставлена как no-op для сохранения цепочки.
"""

# revision identifiers, used by Alembic.
revision = '001_c9e79a48'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
