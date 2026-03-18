"""Расширение investigation_acts → enquiry_acts: nullable FK, новые поля, теги, переименование

Revision ID: 003_enquiry_acts_expand
Revises: 002_inv_acts_recs
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '003_enquiry_acts_expand'
down_revision = '002_inv_acts_recs'
branch_labels = None
depends_on = None


def upgrade():
    # 1. incident_id → nullable
    op.alter_column(
        'investigation_acts', 'incident_id',
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    # 2. Новые колонки
    op.add_column('investigation_acts', sa.Column('link_status', sa.String(50), nullable=False, server_default='Не привязан'))

    op.add_column('investigation_acts', sa.Column('act_type', sa.String(50), nullable=True))
    op.add_column('investigation_acts', sa.Column('act_date', sa.Date(), nullable=True))
    op.add_column('investigation_acts', sa.Column('act_number', sa.String(255), nullable=True))
    op.add_column('investigation_acts', sa.Column('language', sa.String(5), nullable=False, server_default='ru'))
    op.add_column('investigation_acts', sa.Column('file_id', UUID(as_uuid=True), nullable=True))
    op.add_column('investigation_acts', sa.Column('original_filename', sa.String(500), nullable=False, server_default=''))

    # Поля для авто-матчинга
    op.add_column('investigation_acts', sa.Column('incident_date_from_act', sa.Date(), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_name_from_act', sa.String(255), nullable=True))
    op.add_column('investigation_acts', sa.Column('company_name_from_act', sa.String(500), nullable=True))
    op.add_column('investigation_acts', sa.Column('region_from_act', sa.String(255), nullable=True))

    # Комиссия
    op.add_column('investigation_acts', sa.Column('commission_chairman', sa.String(500), nullable=True))
    op.add_column('investigation_acts', sa.Column('commission_members', JSONB(), nullable=False, server_default='[]'))
    op.add_column('investigation_acts', sa.Column('investigation_period', sa.String(255), nullable=True))

    # Сведения о пострадавшем
    op.add_column('investigation_acts', sa.Column('victim_name', sa.String(255), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_birth_date', sa.Date(), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_position', sa.String(255), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_experience', sa.String(255), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_training_dates', sa.Text(), nullable=True))
    op.add_column('investigation_acts', sa.Column('injury_severity', sa.String(100), nullable=True))
    op.add_column('investigation_acts', sa.Column('victim_dependents', sa.Text(), nullable=True))

    # Предприятие
    op.add_column('investigation_acts', sa.Column('company_name', sa.String(500), nullable=True))
    op.add_column('investigation_acts', sa.Column('company_bin', sa.String(20), nullable=True))
    op.add_column('investigation_acts', sa.Column('workplace_description', sa.Text(), nullable=True))

    # Обстоятельства
    op.add_column('investigation_acts', sa.Column('circumstances', sa.Text(), nullable=True))

    # Причины
    op.add_column('investigation_acts', sa.Column('root_causes', sa.Text(), nullable=True))
    op.add_column('investigation_acts', sa.Column('immediate_causes', sa.Text(), nullable=True))
    op.add_column('investigation_acts', sa.Column('state_classifier_codes', JSONB(), nullable=False, server_default='[]'))
    op.add_column('investigation_acts', sa.Column('investigation_method', sa.String(100), nullable=True))

    # Нарушения НПА
    op.add_column('investigation_acts', sa.Column('legal_violations', JSONB(), nullable=False, server_default='[]'))

    # Ответственные лица и мероприятия
    op.add_column('investigation_acts', sa.Column('responsible_persons', JSONB(), nullable=False, server_default='[]'))
    op.add_column('investigation_acts', sa.Column('corrective_measures', JSONB(), nullable=False, server_default='[]'))

    # Выводы
    op.add_column('investigation_acts', sa.Column('work_related', sa.Boolean(), nullable=True))
    op.add_column('investigation_acts', sa.Column('employer_fault_pct', sa.SmallInteger(), nullable=True))
    op.add_column('investigation_acts', sa.Column('worker_fault_pct', sa.SmallInteger(), nullable=True))
    op.add_column('investigation_acts', sa.Column('conclusions', sa.Text(), nullable=True))
    op.add_column('investigation_acts', sa.Column('related_incident_ids', JSONB(), nullable=False, server_default='[]'))

    # AI-анализ
    op.add_column('investigation_acts', sa.Column('ai_summary', sa.Text(), nullable=True))
    op.add_column('investigation_acts', sa.Column('ai_risk_factors', JSONB(), nullable=False, server_default='[]'))

    # Теги для классификации паттернов (TEXT[] с GIN-индексами)
    op.execute("ALTER TABLE investigation_acts ADD COLUMN cause_categories TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE investigation_acts ADD COLUMN violation_types TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE investigation_acts ADD COLUMN industry_tags TEXT[] NOT NULL DEFAULT '{}'")

    # 3. Существующие записи → link_status = 'Автоматически привязан'
    op.execute(
        "UPDATE investigation_acts SET link_status = 'Автоматически привязан' "
        "WHERE incident_id IS NOT NULL"
    )

    # 4. Переименование таблицы
    op.rename_table('investigation_acts', 'enquiry_acts')

    # 5. Переименование индекса
    op.execute('ALTER INDEX ix_investigation_acts_incident_id RENAME TO ix_enquiry_acts_incident_id')

    # 6. Новые индексы
    op.create_index('ix_enquiry_acts_link_status', 'enquiry_acts', ['link_status'])
    op.create_index('ix_enquiry_acts_act_type', 'enquiry_acts', ['act_type'])
    op.create_index('ix_enquiry_acts_incident_date_from_act', 'enquiry_acts', ['incident_date_from_act'])
    op.create_index('ix_enquiry_acts_file_id', 'enquiry_acts', ['file_id'])

    # GIN-индексы для быстрого поиска по тегам
    op.execute('CREATE INDEX ix_enquiry_acts_cause_categories ON enquiry_acts USING GIN(cause_categories)')
    op.execute('CREATE INDEX ix_enquiry_acts_violation_types ON enquiry_acts USING GIN(violation_types)')
    op.execute('CREATE INDEX ix_enquiry_acts_industry_tags ON enquiry_acts USING GIN(industry_tags)')


def downgrade():
    # Удалить GIN-индексы
    op.execute('DROP INDEX IF EXISTS ix_enquiry_acts_industry_tags')
    op.execute('DROP INDEX IF EXISTS ix_enquiry_acts_violation_types')
    op.execute('DROP INDEX IF EXISTS ix_enquiry_acts_cause_categories')

    # Удалить обычные индексы
    op.drop_index('ix_enquiry_acts_file_id', 'enquiry_acts')
    op.drop_index('ix_enquiry_acts_incident_date_from_act', 'enquiry_acts')
    op.drop_index('ix_enquiry_acts_act_type', 'enquiry_acts')
    op.drop_index('ix_enquiry_acts_link_status', 'enquiry_acts')

    # Восстановить имя индекса
    op.execute('ALTER INDEX ix_enquiry_acts_incident_id RENAME TO ix_investigation_acts_incident_id')

    # Переименовать таблицу обратно
    op.rename_table('enquiry_acts', 'investigation_acts')

    # Удалить теги
    op.drop_column('investigation_acts', 'industry_tags')
    op.drop_column('investigation_acts', 'violation_types')
    op.drop_column('investigation_acts', 'cause_categories')

    # Удалить новые колонки (в обратном порядке добавления)
    for col in [
        'ai_risk_factors', 'ai_summary',
        'related_incident_ids', 'conclusions', 'worker_fault_pct', 'employer_fault_pct', 'work_related',
        'corrective_measures', 'responsible_persons',
        'legal_violations',
        'investigation_method', 'state_classifier_codes', 'immediate_causes', 'root_causes',
        'circumstances',
        'workplace_description', 'company_bin', 'company_name',
        'victim_dependents', 'injury_severity', 'victim_training_dates',
        'victim_experience', 'victim_position', 'victim_birth_date', 'victim_name',
        'investigation_period', 'commission_members', 'commission_chairman',
        'region_from_act', 'company_name_from_act', 'victim_name_from_act', 'incident_date_from_act',
        'original_filename', 'file_id', 'language', 'act_number', 'act_date', 'act_type',
        'link_status',
    ]:
        op.drop_column('investigation_acts', col)

    # Восстановить NOT NULL на incident_id
    op.alter_column(
        'investigation_acts', 'incident_id',
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
