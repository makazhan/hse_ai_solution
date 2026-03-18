"""Таблица enquiry_act_chunks для RAG-поиска по актам расследования

Revision ID: 004_enquiry_act_chunks
Revises: 003_enquiry_acts_expand
Create Date: 2026-02-16
"""
import logging
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

_logger = logging.getLogger(__name__)

revision = '004_enquiry_act_chunks'
down_revision = '003_enquiry_acts_expand'
branch_labels = None
depends_on = None


def _has_pgvector() -> bool:
    """Проверяет доступность расширения pgvector."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
        ")"
    ))
    return result.scalar()


def upgrade():
    has_vector = _has_pgvector()

    if has_vector:
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    else:
        _logger.warning(
            "pgvector недоступен — таблица enquiry_act_chunks будет создана "
            "без колонки embedding и без векторного индекса"
        )

    op.create_table(
        'enquiry_act_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('act_id', UUID(as_uuid=True), sa.ForeignKey('enquiry_acts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.SmallInteger(), nullable=False),
        sa.Column('section_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    if has_vector:
        op.execute('ALTER TABLE enquiry_act_chunks ADD COLUMN embedding vector(1024) NOT NULL')
        op.execute(
            'CREATE INDEX ix_eac_embedding ON enquiry_act_chunks '
            'USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)'
        )

    op.create_index('ix_eac_act_id', 'enquiry_act_chunks', ['act_id'])
    op.create_index('ix_eac_section_type', 'enquiry_act_chunks', ['section_type'])


def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_eac_embedding')
    op.drop_index('ix_eac_section_type', 'enquiry_act_chunks')
    op.drop_index('ix_eac_act_id', 'enquiry_act_chunks')
    op.drop_table('enquiry_act_chunks')
