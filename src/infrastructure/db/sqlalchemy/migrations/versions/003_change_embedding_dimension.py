"""Change embedding dimension from 1536 to 1024

Revision ID: 003_change_embedding_dimension
Revises: 002_npa_schema
Create Date: 2026-01-25 14:00:00.000000

NOTE: Изменяла norm_embeddings из 002_npa_schema, которая теперь no-op.
Миграция оставлена как no-op для сохранения цепочки.
"""

revision = '003_change_embedding_dimension'
down_revision = '002_npa_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
