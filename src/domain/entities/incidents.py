import datetime
import uuid
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
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


class Incident(BaseModel):
    """Сущность инцидента ТБ.

    NOTE: используется Pydantic BaseModel, а не dataclass+BaseEntity.
    Из-за этого Incident не поддерживает domain events (register_event/pull_events).
    Если потребуется публикация IncidentCreatedEvent — перевести на dataclass+BaseEntity
    или добавить Pydantic-совместимый EventMixin.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Поле «№» опущено — относится к слою представления
    id: UUID = Field(default_factory=uuid.uuid4)
    incident_date: datetime.date
    incident_time: Optional[datetime.time] = None

    company: Company = Field(default=Company.KAZAKHTELECOM)
    dzo: Optional[str] = None  # ДЗО

    classification: IncidentClassification = Field(default=IncidentClassification.WORK_ACCIDENT)
    region: Region = Field(default=Region.ALMATY_CITY)
    location: str = ""

    victim_name: Optional[str] = None
    victim_birth_date: Optional[datetime.date] = None
    victim_position: Optional[str] = None
    victim_work_experience: Optional[WorkExperience] = None

    injury_type: Optional[InjuryType] = None
    diagnosis: Optional[str] = None

    description: str = ""

    initial_actions: Optional[str] = None

    consequences_elimination_date: Optional[datetime.date] = None
    consequences_elimination_time: Optional[datetime.time] = None

    impact_on_production: Optional[str] = None
    notified_authorities: Optional[str] = None

    preliminary_causes: Optional[str] = None
    consequences_description: Optional[str] = None
    damage_amount_kzt: Optional[float] = None

    investigation_results: Optional[InvestigationResult] = None
    main_causes_from_report: Optional[str] = None
    corrective_actions: Optional[str] = None
    corrective_actions_execution_report: Optional[str] = None
    root_causes: Optional[str] = None

    notes: Optional[str] = None
    investigation_status: InvestigationStatus = Field(default=InvestigationStatus.NOT_COMPLETED)
    deletion_status: Optional[DeletionStatus] = None

    # --- Фаза A: текстовые колонки ---
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # --- Фаза B: счётчики ---
    victim_count: int = 1
    fatality_count: int = 0

    # --- Фаза C: булевые AI-зависимые ---
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class EnquiryAct(BaseModel):
    """Акт расследования несчастного случая.

    incident_id — Optional,
    акт может быть загружен до привязки к инциденту.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    incident_id: Optional[UUID] = None

    # --- Статус привязки ---
    link_status: EnquiryActLinkStatus = EnquiryActLinkStatus.UNLINKED

    # --- Метаданные документа ---
    act_type: Optional[EnquiryActType] = None
    act_date: Optional[datetime.date] = None
    act_number: Optional[str] = None
    language: str = "ru"

    # --- Файл и OCR ---
    file_path: str = ""
    file_id: Optional[UUID] = None  # FK → uploaded_files
    original_filename: str = ""
    extracted_text: str = ""
    analysis_result: str = ""  # Обратная совместимость с текущим upload handler

    # --- Комиссия ---
    commission_chairman: Optional[str] = None
    commission_members: list[str] = Field(default_factory=list)
    investigation_period: Optional[str] = None

    # --- Поля для авто-матчинга с инцидентом ---
    incident_date_from_act: Optional[datetime.date] = None
    victim_name_from_act: Optional[str] = None
    company_name_from_act: Optional[str] = None
    region_from_act: Optional[str] = None

    # --- Сведения о пострадавшем (из акта) ---
    victim_name: Optional[str] = None
    victim_birth_date: Optional[datetime.date] = None
    victim_position: Optional[str] = None
    victim_experience: Optional[str] = None
    victim_training_dates: Optional[str] = None
    injury_severity: Optional[str] = None
    victim_dependents: Optional[str] = None

    # --- Предприятие ---
    company_name: Optional[str] = None
    company_bin: Optional[str] = None
    workplace_description: Optional[str] = None

    # --- Обстоятельства ---
    circumstances: Optional[str] = None

    # --- Причины ---
    root_causes: Optional[str] = None
    immediate_causes: Optional[str] = None
    state_classifier_codes: list[str] = Field(default_factory=list)
    investigation_method: Optional[str] = None

    # --- Нарушения НПА ---
    legal_violations: list[str] = Field(default_factory=list)

    # --- Ответственные лица ---
    responsible_persons: list[dict] = Field(default_factory=list)

    # --- Мероприятия ---
    corrective_measures: list[dict] = Field(default_factory=list)

    # --- Выводы ---
    work_related: Optional[bool] = None
    employer_fault_pct: Optional[int] = None
    worker_fault_pct: Optional[int] = None
    conclusions: Optional[str] = None
    related_incident_ids: list[UUID] = Field(default_factory=list)

    # --- AI-анализ ---
    ai_summary: Optional[str] = None
    ai_risk_factors: list[str] = Field(default_factory=list)

    # --- Теги для классификации паттернов ---
    cause_categories: list[str] = Field(default_factory=list)
    violation_types: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)

    # --- Timestamps ---
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)



class EnquiryActChunk(BaseModel):
    """Чанк акта расследования для RAG-поиска"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    act_id: UUID
    chunk_index: int
    section_type: str
    content: str
    embedding: list[float] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class Recommendation(BaseModel):
    """Рекомендация по ТБ"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    incident_id: UUID
    recommendation_text: str
    priority: RecommendationPriority
    status: RecommendationStatus
    legal_references: list[str] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
