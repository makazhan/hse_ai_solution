"""Замена нормализованной 8-табличной NPA-схемы на плоские chunk-таблицы
из agent-tb-api. Добавление таблиц ВНД и белого списка doc_id.

Revision ID: 009_npa_flat_schema
Revises: 008_count_training_cols
Create Date: 2026-03-04
"""
import logging
from alembic import op
import sqlalchemy as sa


_logger = logging.getLogger(__name__)

revision = '009_npa_flat_schema'
down_revision = '008_count_training_cols'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Проверяет существование таблицы в БД."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_schema = 'public' AND table_name = :t"
        ")"
    ), {"t": table_name})
    return result.scalar()


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
    import os
    # Если справочники живут на отдельном хосте — таблицы управляются извне,
    # создавать их в основной БД не нужно.
    if os.environ.get('REFS_POSTGRES_HOST'):
        return

    has_vector = _has_pgvector()
    if has_vector:
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    else:
        _logger.warning(
            "pgvector недоступен — NPA/VND таблицы будут созданы "
            "без колонок embedding и без векторных индексов"
        )

    # -- Метаданные НПА (RU) --
    if not _table_exists('all_laws_metadata_ru'):
        op.create_table(
            'all_laws_metadata_ru',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('ngr', sa.Text(), nullable=True),
            sa.Column('language', sa.Text(), nullable=True),
            sa.Column('versions_count', sa.Text(), nullable=True),
            sa.Column('actTypes', sa.Text(), nullable=True),
            sa.Column('status', sa.Text(), nullable=True),
            sa.Column('version_date', sa.Text(), nullable=True),
            sa.Column('state_agency_doc_number', sa.Text(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('requisites', sa.Text(), nullable=True),
            sa.Column('adilet_link', sa.Text(), nullable=True),
        )

    # -- Метаданные НПА (KZ) --
    if not _table_exists('all_laws_metadata_kz'):
        op.create_table(
            'all_laws_metadata_kz',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('ngr', sa.Text(), nullable=True),
            sa.Column('language', sa.Text(), nullable=True),
            sa.Column('versions_count', sa.Text(), nullable=True),
            sa.Column('actTypes', sa.Text(), nullable=True),
            sa.Column('status', sa.Text(), nullable=True),
            sa.Column('version_date', sa.Text(), nullable=True),
            sa.Column('state_agency_doc_number', sa.Text(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('requisites', sa.Text(), nullable=True),
            sa.Column('adilet_link', sa.Text(), nullable=True),
        )

    # -- Чанки НПА (RU) с эмбеддингами --
    if not _table_exists('all_laws_ru'):
        cols = [
            sa.Column('row_id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('doc_id', sa.Text(), sa.ForeignKey('all_laws_metadata_ru.id'), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
            sa.Column('chunk', sa.Text(), nullable=True),
        ]
        if has_vector:
            from pgvector.sqlalchemy import Vector
            cols.append(sa.Column('embedding', Vector(1024), nullable=True))
        op.create_table('all_laws_ru', *cols)

    # -- Чанки НПА (KZ) --
    if not _table_exists('all_laws_kz'):
        cols = [
            sa.Column('row_id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('doc_id', sa.Text(), sa.ForeignKey('all_laws_metadata_kz.id'), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
            sa.Column('chunk', sa.Text(), nullable=True),
        ]
        if has_vector:
            from pgvector.sqlalchemy import Vector
            cols.append(sa.Column('embedding', Vector(1024), nullable=True))
        op.create_table('all_laws_kz', *cols)

    # -- Белый список doc_id для фильтрации поиска --
    if not _table_exists('safety_tb_npa'):
        op.create_table(
            'safety_tb_npa',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('doc_id', sa.Text(), nullable=True),
        )

    # -- ВНД (внутренние нормативные документы) --
    if not _table_exists('safety_tb_vnd'):
        cols = [
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('doc_path', sa.Text(), nullable=True),
            sa.Column('doc_title_without_transl', sa.Text(), nullable=True),
            sa.Column('doc_title_with_transl', sa.Text(), nullable=True),
            sa.Column('chunk_index', sa.SmallInteger(), nullable=True),
            sa.Column('chunk_text', sa.Text(), nullable=True),
            sa.Column('file_name_minio', sa.Text(), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
        ]
        if has_vector:
            from pgvector.sqlalchemy import Vector
            cols.append(sa.Column('dense_embedding', Vector(1024), nullable=True))
        op.create_table('safety_tb_vnd', *cols)


def downgrade():
    # Удаляем только те таблицы, которые создала эта миграция
    # (FK порядок: сначала дочерние, потом родительские)
    for table in (
        'safety_tb_vnd', 'safety_tb_npa',
        'all_laws_kz', 'all_laws_ru',
        'all_laws_metadata_kz', 'all_laws_metadata_ru',
    ):
        if _table_exists(table):
            op.drop_table(table)
