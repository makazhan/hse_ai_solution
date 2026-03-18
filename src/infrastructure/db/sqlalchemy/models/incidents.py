import uuid
import datetime
from datetime import date, time
from typing import Optional

from sqlalchemy import String, Date, Time, Float, JSON, Boolean, SmallInteger, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from src.domain.entities.incidents import (
    Incident, EnquiryAct, EnquiryActChunk, Recommendation,
)
from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    Region,
    InjuryType,
    InvestigationResult,
    InvestigationStatus,
    WorkExperience,
    DeletionStatus,
    RecommendationPriority,
    RecommendationStatus,
    EnquiryActType,
    EnquiryActLinkStatus,
)
from src.infrastructure.db.sqlalchemy.models.base import TimedBaseModel


class IncidentModel(TimedBaseModel):
    """Модель происшествия ТБ"""
    __tablename__ = 'incidents'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    incident_date: Mapped[date] = mapped_column(Date)
    incident_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    company: Mapped[Company] = mapped_column(String(255))
    dzo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    classification: Mapped[IncidentClassification] = mapped_column(String(255))
    region: Mapped[Region] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(500))
    
    victim_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    victim_position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_work_experience: Mapped[Optional[WorkExperience]] = mapped_column(String(50), nullable=True)
    
    injury_type: Mapped[Optional[InjuryType]] = mapped_column(String(50), nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    description: Mapped[str] = mapped_column(String)
    
    initial_actions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    consequences_elimination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consequences_elimination_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    impact_on_production: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notified_authorities: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    preliminary_causes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    consequences_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    damage_amount_kzt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    investigation_results: Mapped[Optional[InvestigationResult]] = mapped_column(String(50), nullable=True)
    main_causes_from_report: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    corrective_actions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    corrective_actions_execution_report: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    root_causes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    investigation_status: Mapped[InvestigationStatus] = mapped_column(String(50))
    deletion_status: Mapped[Optional[DeletionStatus]] = mapped_column(String(50), nullable=True)

    # Фаза A: текстовые колонки
    work_type: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    equipment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    safety_responsible_person: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    weather_conditions: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Фаза B: счётчики
    victim_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default='1')
    fatality_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default='0')

    # Фаза C: булевые AI-зависимые
    safety_training_completed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_recurrent: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    regulatory_compliant: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    @classmethod
    def from_entity(cls, entity: Incident) -> 'IncidentModel':
        """Entity → Model"""
        return cls(
            id=entity.id,
            incident_date=entity.incident_date,
            incident_time=entity.incident_time,
            company=entity.company,
            dzo=entity.dzo,
            classification=entity.classification,
            region=entity.region,
            location=entity.location,
            victim_name=entity.victim_name,
            victim_birth_date=entity.victim_birth_date,
            victim_position=entity.victim_position,
            victim_work_experience=entity.victim_work_experience,
            injury_type=entity.injury_type,
            diagnosis=entity.diagnosis,
            description=entity.description,
            initial_actions=entity.initial_actions,
            consequences_elimination_date=entity.consequences_elimination_date,
            consequences_elimination_time=entity.consequences_elimination_time,
            impact_on_production=entity.impact_on_production,
            notified_authorities=entity.notified_authorities,
            preliminary_causes=entity.preliminary_causes,
            consequences_description=entity.consequences_description,
            damage_amount_kzt=entity.damage_amount_kzt,
            investigation_results=entity.investigation_results,
            main_causes_from_report=entity.main_causes_from_report,
            corrective_actions=entity.corrective_actions,
            corrective_actions_execution_report=entity.corrective_actions_execution_report,
            root_causes=entity.root_causes,
            notes=entity.notes,
            investigation_status=entity.investigation_status,
            deletion_status=entity.deletion_status,
            work_type=entity.work_type,
            equipment=entity.equipment,
            safety_responsible_person=entity.safety_responsible_person,
            weather_conditions=entity.weather_conditions,
            victim_count=entity.victim_count,
            fatality_count=entity.fatality_count,
            safety_training_completed=entity.safety_training_completed,
            is_recurrent=entity.is_recurrent,
            regulatory_compliant=entity.regulatory_compliant,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Incident:
        """Model → Entity"""
        return Incident(
            id=self.id,
            incident_date=self.incident_date,
            incident_time=self.incident_time,
            company=self.company,
            dzo=self.dzo,
            classification=self.classification,
            region=self.region,
            location=self.location,
            victim_name=self.victim_name,
            victim_birth_date=self.victim_birth_date,
            victim_position=self.victim_position,
            victim_work_experience=self.victim_work_experience,
            injury_type=self.injury_type,
            diagnosis=self.diagnosis,
            description=self.description,
            initial_actions=self.initial_actions,
            consequences_elimination_date=self.consequences_elimination_date,
            consequences_elimination_time=self.consequences_elimination_time,
            impact_on_production=self.impact_on_production,
            notified_authorities=self.notified_authorities,
            preliminary_causes=self.preliminary_causes,
            consequences_description=self.consequences_description,
            damage_amount_kzt=self.damage_amount_kzt,
            investigation_results=self.investigation_results,
            main_causes_from_report=self.main_causes_from_report,
            corrective_actions=self.corrective_actions,
            corrective_actions_execution_report=self.corrective_actions_execution_report,
            root_causes=self.root_causes,
            notes=self.notes,
            investigation_status=self.investigation_status,
            deletion_status=self.deletion_status,
            work_type=self.work_type,
            equipment=self.equipment,
            safety_responsible_person=self.safety_responsible_person,
            weather_conditions=self.weather_conditions,
            victim_count=self.victim_count,
            fatality_count=self.fatality_count,
            safety_training_completed=self.safety_training_completed,
            is_recurrent=self.is_recurrent,
            regulatory_compliant=self.regulatory_compliant,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class EnquiryActModel(TimedBaseModel):
    """Модель акта расследования"""
    __tablename__ = 'enquiry_acts'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id', ondelete='CASCADE'), nullable=True, index=True)

    # Статус привязки
    link_status: Mapped[str] = mapped_column(String(50), nullable=False, default='Не привязан')

    # Метаданные документа
    act_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    act_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    act_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default='ru')

    # Файл и OCR
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default='')
    analysis_result: Mapped[str] = mapped_column(Text, nullable=False, default='')

    # Комиссия
    commission_chairman: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    commission_members: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    investigation_period: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Поля для авто-матчинга
    incident_date_from_act: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    victim_name_from_act: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name_from_act: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    region_from_act: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Сведения о пострадавшем
    victim_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    victim_position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_experience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_training_dates: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    injury_severity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    victim_dependents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Предприятие
    company_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    company_bin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    workplace_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Обстоятельства
    circumstances: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Причины
    root_causes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    immediate_causes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state_classifier_codes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    investigation_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Нарушения НПА
    legal_violations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Ответственные лица и мероприятия
    responsible_persons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    corrective_measures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Выводы
    work_related: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    employer_fault_pct: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    worker_fault_pct: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    conclusions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_incident_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # AI-анализ
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_risk_factors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Теги для классификации паттернов (TEXT[] с GIN-индексами)
    cause_categories: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=False, server_default='{}')
    violation_types: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=False, server_default='{}')
    industry_tags: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=False, server_default='{}')

    # Timestamps
    uploaded_at: Mapped[datetime.datetime] = mapped_column(nullable=False)

    @classmethod
    def from_entity(cls, entity: EnquiryAct) -> 'EnquiryActModel':
        return cls(
            id=entity.id,
            incident_id=entity.incident_id,
            link_status=entity.link_status.value if entity.link_status else 'Не привязан',
            act_type=entity.act_type.value if entity.act_type else None,
            act_date=entity.act_date,
            act_number=entity.act_number,
            language=entity.language,
            file_path=entity.file_path,
            file_id=entity.file_id,
            original_filename=entity.original_filename,
            extracted_text=entity.extracted_text,
            analysis_result=entity.analysis_result,
            commission_chairman=entity.commission_chairman,
            commission_members=entity.commission_members,
            investigation_period=entity.investigation_period,
            incident_date_from_act=entity.incident_date_from_act,
            victim_name_from_act=entity.victim_name_from_act,
            company_name_from_act=entity.company_name_from_act,
            region_from_act=entity.region_from_act,
            victim_name=entity.victim_name,
            victim_birth_date=entity.victim_birth_date,
            victim_position=entity.victim_position,
            victim_experience=entity.victim_experience,
            victim_training_dates=entity.victim_training_dates,
            injury_severity=entity.injury_severity,
            victim_dependents=entity.victim_dependents,
            company_name=entity.company_name,
            company_bin=entity.company_bin,
            workplace_description=entity.workplace_description,
            circumstances=entity.circumstances,
            root_causes=entity.root_causes,
            immediate_causes=entity.immediate_causes,
            state_classifier_codes=entity.state_classifier_codes,
            investigation_method=entity.investigation_method,
            legal_violations=entity.legal_violations,
            responsible_persons=entity.responsible_persons,
            corrective_measures=entity.corrective_measures,
            work_related=entity.work_related,
            employer_fault_pct=entity.employer_fault_pct,
            worker_fault_pct=entity.worker_fault_pct,
            conclusions=entity.conclusions,
            related_incident_ids=[str(uid) for uid in entity.related_incident_ids],
            ai_summary=entity.ai_summary,
            ai_risk_factors=entity.ai_risk_factors,
            cause_categories=entity.cause_categories,
            violation_types=entity.violation_types,
            industry_tags=entity.industry_tags,
            uploaded_at=entity.uploaded_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> EnquiryAct:
        from uuid import UUID as _UUID

        def _safe_uuid(val) -> _UUID:
            """Безопасное преобразование строки в UUID."""
            if isinstance(val, _UUID):
                return val
            try:
                return _UUID(str(val))
            except (ValueError, AttributeError):
                return _UUID(int=0)

        return EnquiryAct(
            id=self.id,
            incident_id=self.incident_id,
            link_status=EnquiryActLinkStatus(self.link_status) if self.link_status else EnquiryActLinkStatus.UNLINKED,
            act_type=EnquiryActType(self.act_type) if self.act_type else None,
            act_date=self.act_date,
            act_number=self.act_number,
            language=self.language or 'ru',
            file_path=self.file_path or '',
            file_id=self.file_id,
            original_filename=self.original_filename or '',
            extracted_text=self.extracted_text or '',
            analysis_result=self.analysis_result or '',
            commission_chairman=self.commission_chairman,
            commission_members=self.commission_members or [],
            investigation_period=self.investigation_period,
            incident_date_from_act=self.incident_date_from_act,
            victim_name_from_act=self.victim_name_from_act,
            company_name_from_act=self.company_name_from_act,
            region_from_act=self.region_from_act,
            victim_name=self.victim_name,
            victim_birth_date=self.victim_birth_date,
            victim_position=self.victim_position,
            victim_experience=self.victim_experience,
            victim_training_dates=self.victim_training_dates,
            injury_severity=self.injury_severity,
            victim_dependents=self.victim_dependents,
            company_name=self.company_name,
            company_bin=self.company_bin,
            workplace_description=self.workplace_description,
            circumstances=self.circumstances,
            root_causes=self.root_causes,
            immediate_causes=self.immediate_causes,
            state_classifier_codes=self.state_classifier_codes or [],
            investigation_method=self.investigation_method,
            legal_violations=self.legal_violations or [],
            responsible_persons=self.responsible_persons or [],
            corrective_measures=self.corrective_measures or [],
            work_related=self.work_related,
            employer_fault_pct=self.employer_fault_pct,
            worker_fault_pct=self.worker_fault_pct,
            conclusions=self.conclusions,
            related_incident_ids=[_safe_uuid(uid) for uid in (self.related_incident_ids or [])],
            ai_summary=self.ai_summary,
            ai_risk_factors=self.ai_risk_factors or [],
            cause_categories=list(self.cause_categories or []),
            violation_types=list(self.violation_types or []),
            industry_tags=list(self.industry_tags or []),
            uploaded_at=self.uploaded_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )



class EnquiryActChunkModel(TimedBaseModel):
    """Модель чанка акта расследования для RAG-поиска"""
    __tablename__ = 'enquiry_act_chunks'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    act_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('enquiry_acts.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1024), nullable=False)

    @classmethod
    def from_entity(cls, entity: EnquiryActChunk) -> 'EnquiryActChunkModel':
        return cls(
            id=entity.id,
            act_id=entity.act_id,
            chunk_index=entity.chunk_index,
            section_type=entity.section_type,
            content=entity.content,
            embedding=entity.embedding,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> EnquiryActChunk:
        return EnquiryActChunk(
            id=self.id,
            act_id=self.act_id,
            chunk_index=self.chunk_index,
            section_type=self.section_type,
            content=self.content,
            embedding=list(self.embedding) if self.embedding is not None else [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class RecommendationModel(TimedBaseModel):
    """Модель рекомендации по ТБ"""
    __tablename__ = 'recommendations'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False, index=True)
    recommendation_text: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    legal_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    @classmethod
    def from_entity(cls, entity: Recommendation) -> 'RecommendationModel':
        return cls(
            id=entity.id,
            incident_id=entity.incident_id,
            recommendation_text=entity.recommendation_text,
            priority=entity.priority.value,
            status=entity.status.value,
            legal_references=entity.legal_references,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Recommendation:
        return Recommendation(
            id=self.id,
            incident_id=self.incident_id,
            recommendation_text=self.recommendation_text,
            priority=RecommendationPriority(self.priority),
            status=RecommendationStatus(self.status),
            legal_references=self.legal_references or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )