"""Create incidents table aligned to IncidentModel

Revision ID: 001_incidents
Revises: 005_add_cascade_delete
Create Date: 2026-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '001_incidents'
down_revision = '005_add_cascade_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'incidents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_date', sa.Date, nullable=False),
        sa.Column('incident_time', sa.Time, nullable=True),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('dzo', sa.String(255), nullable=True),
        sa.Column('classification', sa.String(255), nullable=False),
        sa.Column('region', sa.String(100), nullable=False),
        sa.Column('location', sa.String(500), nullable=False),
        sa.Column('victim_name', sa.String(255), nullable=True),
        sa.Column('victim_birth_date', sa.Date, nullable=True),
        sa.Column('victim_position', sa.String(255), nullable=True),
        sa.Column('victim_work_experience', sa.String(50), nullable=True),
        sa.Column('injury_type', sa.String(50), nullable=True),
        sa.Column('diagnosis', sa.String(1000), nullable=True),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('initial_actions', sa.String, nullable=True),
        sa.Column('consequences_elimination_date', sa.Date, nullable=True),
        sa.Column('consequences_elimination_time', sa.Time, nullable=True),
        sa.Column('impact_on_production', sa.String, nullable=True),
        sa.Column('notified_authorities', sa.String, nullable=True),
        sa.Column('preliminary_causes', sa.String, nullable=True),
        sa.Column('consequences_description', sa.String, nullable=True),
        sa.Column('damage_amount_kzt', sa.Float, nullable=True),
        sa.Column('investigation_results', sa.String(50), nullable=True),
        sa.Column('main_causes_from_report', sa.String, nullable=True),
        sa.Column('corrective_actions', sa.String, nullable=True),
        sa.Column('corrective_actions_execution_report', sa.String, nullable=True),
        sa.Column('root_causes', sa.String, nullable=True),
        sa.Column('notes', sa.String, nullable=True),
        sa.Column('investigation_status', sa.String(50), nullable=False),
        sa.Column('deletion_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_index('idx_incidents_date', 'incidents', ['incident_date'])
    op.create_index('idx_incidents_company', 'incidents', ['company'])
    op.create_index('idx_incidents_region', 'incidents', ['region'])
    op.create_index('idx_incidents_classification', 'incidents', ['classification'])
    op.create_index('idx_incidents_injury_type', 'incidents', ['injury_type'])


def downgrade() -> None:
    op.drop_index('idx_incidents_injury_type', table_name='incidents')
    op.drop_index('idx_incidents_classification', table_name='incidents')
    op.drop_index('idx_incidents_region', table_name='incidents')
    op.drop_index('idx_incidents_company', table_name='incidents')
    op.drop_index('idx_incidents_date', table_name='incidents')
    op.drop_table('incidents')
