from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.enums.incidents import Company, EnquiryActType, EnquiryActLinkStatus, Region


class EnquiryActFiltersSchema(BaseModel):
    """Схема фильтров актов расследования (query params)"""
    act_type: Optional[str] = None
    link_status: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    victim_name: Optional[str] = None
    company_name: Optional[str] = None
    companies: Optional[list[str]] = None
    region: Optional[str] = None
    regions: Optional[list[str]] = None
    language: Optional[str] = None
    incident_id: Optional[str] = None
    cause_category: Optional[str] = None
    violation_type: Optional[str] = None
    industry_tag: Optional[str] = None

    @field_validator('incident_id')
    @classmethod
    def validate_incident_id(cls, v: Optional[str]) -> Optional[str]:
        """Валидация формата UUID."""
        if v is None:
            return v
        try:
            UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый формат UUID: {v}")

    @field_validator('act_type')
    @classmethod
    def validate_act_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            EnquiryActType(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый тип акта: {v}")

    @field_validator('link_status')
    @classmethod
    def validate_link_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            EnquiryActLinkStatus(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый статус привязки: {v}")

    @field_validator('companies')
    @classmethod
    def validate_companies(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Валидация списка компаний."""
        if v is None:
            return v
        for item in v:
            try:
                Company(item)
            except ValueError:
                allowed = ", ".join(e.value for e in Company)
                raise ValueError(f"Недопустимая компания: {item}. Допустимые: {allowed}")
        return v

    @field_validator('regions')
    @classmethod
    def validate_regions(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Валидация списка регионов."""
        if v is None:
            return v
        for item in v:
            try:
                Region(item)
            except ValueError:
                allowed = ", ".join(e.value for e in Region)
                raise ValueError(f"Недопустимый регион: {item}. Допустимые: {allowed}")
        return v

    @model_validator(mode='after')
    def validate_mutual_exclusion(self) -> 'EnquiryActFiltersSchema':
        """Взаимоисключение одиночных и множественных фильтров."""
        if self.company_name and self.companies:
            raise ValueError("Нельзя указывать company_name и companies одновременно")
        if self.region and self.regions:
            raise ValueError("Нельзя указывать region и regions одновременно")
        return self


class EnquiryActResponseSchema(BaseModel):
    """Полная схема ответа акта расследования"""
    id: UUID
    incident_id: Optional[UUID] = None
    link_status: str
    act_type: Optional[str] = None
    act_date: Optional[date] = None
    act_number: Optional[str] = None
    language: str = "ru"

    # Файл
    file_path: str = ""
    file_id: Optional[UUID] = None
    original_filename: str = ""
    extracted_text: str = ""

    # Комиссия
    commission_chairman: Optional[str] = None
    commission_members: list[str] = Field(default_factory=list)
    investigation_period: Optional[str] = None

    # Авто-матчинг
    incident_date_from_act: Optional[date] = None
    victim_name_from_act: Optional[str] = None
    company_name_from_act: Optional[str] = None
    region_from_act: Optional[str] = None

    # Пострадавший
    victim_name: Optional[str] = None
    victim_birth_date: Optional[date] = None
    victim_position: Optional[str] = None
    victim_experience: Optional[str] = None
    victim_training_dates: Optional[str] = None
    injury_severity: Optional[str] = None
    victim_dependents: Optional[str] = None

    # Предприятие
    company_name: Optional[str] = None
    company_bin: Optional[str] = None
    workplace_description: Optional[str] = None

    # Обстоятельства и причины
    circumstances: Optional[str] = None
    root_causes: Optional[str] = None
    immediate_causes: Optional[str] = None
    state_classifier_codes: list[str] = Field(default_factory=list)
    investigation_method: Optional[str] = None
    legal_violations: list[str] = Field(default_factory=list)

    # Ответственные и мероприятия
    responsible_persons: list[dict] = Field(default_factory=list)
    corrective_measures: list[dict] = Field(default_factory=list)

    # Выводы
    work_related: Optional[bool] = None
    employer_fault_pct: Optional[int] = None
    worker_fault_pct: Optional[int] = None
    conclusions: Optional[str] = None
    related_incident_ids: list[UUID] = Field(default_factory=list)

    # AI-анализ
    ai_summary: Optional[str] = None
    ai_risk_factors: list[str] = Field(default_factory=list)

    # Теги
    cause_categories: list[str] = Field(default_factory=list)
    violation_types: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)

    # Timestamps
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, act) -> 'EnquiryActResponseSchema':
        """Маппинг EnquiryAct → схема ответа."""
        return cls(
            id=act.id,
            incident_id=act.incident_id,
            link_status=act.link_status.value if hasattr(act.link_status, 'value') else act.link_status,
            act_type=act.act_type.value if act.act_type and hasattr(act.act_type, 'value') else act.act_type,
            act_date=act.act_date,
            act_number=act.act_number,
            language=act.language,
            file_path=act.file_path,
            file_id=act.file_id,
            original_filename=act.original_filename,
            extracted_text=act.extracted_text,
            commission_chairman=act.commission_chairman,
            commission_members=act.commission_members,
            investigation_period=act.investigation_period,
            incident_date_from_act=act.incident_date_from_act,
            victim_name_from_act=act.victim_name_from_act,
            company_name_from_act=act.company_name_from_act,
            region_from_act=act.region_from_act,
            victim_name=act.victim_name,
            victim_birth_date=act.victim_birth_date,
            victim_position=act.victim_position,
            victim_experience=act.victim_experience,
            victim_training_dates=act.victim_training_dates,
            injury_severity=act.injury_severity,
            victim_dependents=act.victim_dependents,
            company_name=act.company_name,
            company_bin=act.company_bin,
            workplace_description=act.workplace_description,
            circumstances=act.circumstances,
            root_causes=act.root_causes,
            immediate_causes=act.immediate_causes,
            state_classifier_codes=act.state_classifier_codes,
            investigation_method=act.investigation_method,
            legal_violations=act.legal_violations,
            responsible_persons=act.responsible_persons,
            corrective_measures=act.corrective_measures,
            work_related=act.work_related,
            employer_fault_pct=act.employer_fault_pct,
            worker_fault_pct=act.worker_fault_pct,
            conclusions=act.conclusions,
            related_incident_ids=act.related_incident_ids,
            ai_summary=act.ai_summary,
            ai_risk_factors=act.ai_risk_factors,
            cause_categories=act.cause_categories,
            violation_types=act.violation_types,
            industry_tags=act.industry_tags,
            uploaded_at=act.uploaded_at,
            created_at=act.created_at,
            updated_at=act.updated_at,
        )


class EnquiryActBriefSchema(BaseModel):
    """Краткая схема акта (для списков)"""
    id: UUID
    incident_id: Optional[UUID] = None
    link_status: str
    act_type: Optional[str] = None
    act_date: Optional[date] = None
    language: str = "ru"
    original_filename: str = ""
    victim_name: Optional[str] = None
    company_name: Optional[str] = None
    cause_categories: list[str] = Field(default_factory=list)
    violation_types: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)
    uploaded_at: datetime

    @classmethod
    def from_entity(cls, act) -> 'EnquiryActBriefSchema':
        return cls(
            id=act.id,
            incident_id=act.incident_id,
            link_status=act.link_status.value if hasattr(act.link_status, 'value') else act.link_status,
            act_type=act.act_type.value if act.act_type and hasattr(act.act_type, 'value') else act.act_type,
            act_date=act.act_date,
            language=act.language,
            original_filename=act.original_filename,
            victim_name=act.victim_name,
            company_name=act.company_name,
            cause_categories=act.cause_categories,
            violation_types=act.violation_types,
            industry_tags=act.industry_tags,
            uploaded_at=act.uploaded_at,
        )


class PaginatedEnquiryActsResponseSchema(BaseModel):
    """Схема ответа списка актов с пагинацией"""
    items: list[EnquiryActBriefSchema]
    total: int
    limit: int
    offset: int


class TagPatternSchema(BaseModel):
    """Паттерн тега с количеством"""
    tag: str
    count: int


class TagPatternsResponseSchema(BaseModel):
    """Схема ответа агрегации паттернов"""
    cause_categories: list[TagPatternSchema] = Field(default_factory=list)
    violation_types: list[TagPatternSchema] = Field(default_factory=list)
    industry_tags: list[TagPatternSchema] = Field(default_factory=list)


class UploadActFileResultSchema(BaseModel):
    """Результат загрузки одного акта в пакете"""
    file_id: UUID
    act: Optional[EnquiryActBriefSchema] = None
    error: Optional[str] = None


class UploadActsBatchResponseSchema(BaseModel):
    """Ответ пакетной загрузки актов"""
    total_files: int
    successful: int
    failed: int
    results: list[UploadActFileResultSchema]
