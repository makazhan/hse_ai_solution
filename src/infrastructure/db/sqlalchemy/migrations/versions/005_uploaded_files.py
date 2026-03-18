"""Таблица uploaded_files + FK enquiry_acts.file_id → uploaded_files.id

Revision ID: 005_uploaded_files
Revises: 004_enquiry_act_chunks
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '005_uploaded_files'
down_revision = '004_enquiry_act_chunks'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'uploaded_files',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(255), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('s3_key', sa.String(1000), nullable=False, unique=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # FK: enquiry_acts.file_id → uploaded_files.id
    op.create_foreign_key(
        'fk_enquiry_acts_file_id',
        'enquiry_acts', 'uploaded_files',
        ['file_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint('fk_enquiry_acts_file_id', 'enquiry_acts', type_='foreignkey')
    op.drop_table('uploaded_files')
