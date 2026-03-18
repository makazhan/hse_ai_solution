"""Удаление таблиц чата (chats, user_messages, agent_responses)

Revision ID: 006_drop_chat_tables
Revises: 005_uploaded_files
Create Date: 2026-02-17

NOTE: 001_c9e79a48 теперь no-op, поэтому таблицы могут не существовать.
DROP IF EXISTS безопасен в обоих случаях.
"""
from alembic import op
import sqlalchemy as sa


revision = '006_drop_chat_tables'
down_revision = '005_uploaded_files'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('DROP TABLE IF EXISTS agent_responses')
    op.execute('DROP TABLE IF EXISTS user_messages')
    op.execute('DROP TABLE IF EXISTS chats')


def downgrade():
    pass
