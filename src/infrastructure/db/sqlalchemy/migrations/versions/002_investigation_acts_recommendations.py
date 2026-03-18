"""Add investigation_acts and recommendations tables

Revision ID: 002_inv_acts_recs
Revises: 001_incidents
Create Date: 2026-02-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = '002_inv_acts_recs'
down_revision = '001_incidents'
branch_labels = None
depends_on = None


def upgrade():
    # Investigation Acts table
    op.create_table(
        'investigation_acts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('extracted_text', sa.String(), nullable=False, server_default=''),
        sa.Column('analysis_result', sa.String(), nullable=False, server_default=''),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_investigation_acts_incident_id', 'investigation_acts', ['incident_id'])

    # Recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_text', sa.String(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('legal_references', JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_recommendations_incident_id', 'recommendations', ['incident_id'])


def downgrade():
    op.drop_index('ix_recommendations_incident_id', 'recommendations')
    op.drop_table('recommendations')
    op.drop_index('ix_investigation_acts_incident_id', 'investigation_acts')
    op.drop_table('investigation_acts')
