from datetime import datetime, date, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    InvestigationResult,
    Region,
    WorkExperience,
    InjuryType,
    RecommendationStatus,
)


# Схемы запросов
class CreateIncidentRequestSchema(BaseModel):
    """Схема создания инцидента"""
    incident_date: date
    incident_time: Optional[time] = None
    company: str  # Company enum value
    dzo: Optional[str] = None
    classification: str  # IncidentClassification enum value
    region: str  # Region enum value
    location: str = ""
    victim_name: Optional[str] = None
    victim_birth_date: Optional[date] = None
    victim_position: Optional[str] = None
    victim_work_experience: Optional[str] = None  # WorkExperience enum value
    injury_type: Optional[str] = None  # InjuryType enum value
    diagnosis: Optional[str] = None
    description: str = ""

    # Фаза A: текстовые
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # Фаза B: счётчики
    victim_count: int = Field(default=1, ge=0)
    fatality_count: int = Field(default=0, ge=0)

    # Фаза C: булевые AI-зависимые
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None

    @field_validator('company')
    @classmethod
    def validate_company(cls, v: str) -> str:
        """Валидация значения перечисления компании"""
        try:
            Company(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимая компания: {v}. Допустимые: {', '.join(c.value for c in Company)}")

    @field_validator('classification')
    @classmethod
    def validate_classification(cls, v: str) -> str:
        """Валидация классификации"""
        try:
            IncidentClassification(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимая классификация: {v}. Допустимые: {', '.join(c.value for c in IncidentClassification)}")

    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Валидация региона"""
        try:
            Region(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый регион: {v}. Допустимые: {', '.join(r.value for r in Region)}")

    @field_validator('victim_work_experience')
    @classmethod
    def validate_work_experience(cls, v: Optional[str]) -> Optional[str]:
        """Валидация стажа работы"""
        if v is None:
            return v
        try:
            WorkExperience(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый стаж: {v}. Допустимые: {', '.join(w.value for w in WorkExperience)}")

    @field_validator('injury_type')
    @classmethod
    def validate_injury_type(cls, v: Optional[str]) -> Optional[str]:
        """Валидация типа травмы"""
        if v is None:
            return v
        try:
            InjuryType(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый тип травмы: {v}. Допустимые: {', '.join(i.value for i in InjuryType)}")


class IncidentFiltersSchema(BaseModel):
    """Схема фильтров"""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    region: Optional[str] = None
    company: Optional[str] = None
    companies: Optional[list[str]] = None
    regions: Optional[list[str]] = None
    classification: Optional[str] = None
    injury_type: Optional[str] = None
    investigation_status: Optional[str] = None
    investigation_results: Optional[str] = None
    work_experience: Optional[str] = None
    victim_name: Optional[str] = None
    victim_position: Optional[str] = None
    dzo: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    cause_search: Optional[str] = None

    # Фаза A: ILIKE текстовый поиск
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # Фаза B: диапазоны (мин/макс)
    victim_count_min: Optional[int] = Field(default=None, ge=0)
    victim_count_max: Optional[int] = Field(default=None, ge=0)
    fatality_count_min: Optional[int] = Field(default=None, ge=0)
    fatality_count_max: Optional[int] = Field(default=None, ge=0)

    # Фаза C: булевые
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None

    # Фаза B: субзапрос по рекомендациям
    recommendation_status: Optional[str] = None

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
                raise ValueError(f"Недопустимая компания: {item}. Допустимые: {', '.join(c.value for c in Company)}")
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
                raise ValueError(f"Недопустимый регион: {item}. Допустимые: {', '.join(r.value for r in Region)}")
        return v

    @field_validator('investigation_results')
    @classmethod
    def validate_investigation_results(cls, v: Optional[str]) -> Optional[str]:
        """Валидация результатов расследования."""
        if v is None:
            return v
        try:
            InvestigationResult(v)
        except ValueError:
            raise ValueError(
                f"Недопустимый результат расследования: {v}. "
                f"Допустимые: {', '.join(r.value for r in InvestigationResult)}"
            )
        return v

    @field_validator('recommendation_status')
    @classmethod
    def validate_recommendation_status(cls, v: Optional[str]) -> Optional[str]:
        """Валидация статуса рекомендаций (enum-значения + 'Нет рекомендаций')."""
        if v is None:
            return v
        valid_values = [s.value for s in RecommendationStatus] + ["Нет рекомендаций"]
        if v not in valid_values:
            raise ValueError(
                f"Недопустимый статус рекомендации: {v}. "
                f"Допустимые: {', '.join(valid_values)}"
            )
        return v

    @model_validator(mode='after')
    def validate_min_max_ranges(self) -> 'IncidentFiltersSchema':
        """Проверка: min не должен превышать max в диапазонных фильтрах."""
        if self.victim_count_min is not None and self.victim_count_max is not None:
            if self.victim_count_min > self.victim_count_max:
                raise ValueError("victim_count_min не может превышать victim_count_max")
        if self.fatality_count_min is not None and self.fatality_count_max is not None:
            if self.fatality_count_min > self.fatality_count_max:
                raise ValueError("fatality_count_min не может превышать fatality_count_max")
        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValueError("date_from не может быть позже date_to")
        if self.time_from is not None and self.time_to is not None:
            if self.time_from > self.time_to:
                raise ValueError("time_from не может быть позже time_to")
        # Взаимоисключение: одиночный и множественный фильтр одновременно
        if self.company and self.companies:
            raise ValueError("Нельзя указывать company и companies одновременно")
        if self.region and self.regions:
            raise ValueError("Нельзя указывать region и regions одновременно")
        return self


# Схемы ответов
class IncidentResponseSchema(BaseModel):
    """Схема ответа инцидента"""
    id: UUID
    incident_date: date
    incident_time: Optional[time]
    company: str
    dzo: Optional[str]
    classification: str
    region: str
    location: str
    victim_name: Optional[str]
    victim_birth_date: Optional[date]
    victim_position: Optional[str]
    victim_work_experience: Optional[str]
    injury_type: Optional[str]
    diagnosis: Optional[str]
    description: str
    investigation_status: str

    # Фаза A: текстовые
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # Фаза B: счётчики
    victim_count: int = 1
    fatality_count: int = 0

    # Фаза C: булевые AI-зависимые
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, incident) -> 'IncidentResponseSchema':
        """Маппинг доменной сущности Incident → схема ответа."""
        return cls(
            id=incident.id,
            incident_date=incident.incident_date,
            incident_time=incident.incident_time,
            company=incident.company.value if hasattr(incident.company, 'value') else incident.company,
            dzo=incident.dzo,
            classification=incident.classification.value if hasattr(incident.classification, 'value') else incident.classification,
            region=incident.region.value if hasattr(incident.region, 'value') else incident.region,
            location=incident.location,
            victim_name=incident.victim_name,
            victim_birth_date=incident.victim_birth_date,
            victim_position=incident.victim_position,
            victim_work_experience=incident.victim_work_experience.value if incident.victim_work_experience and hasattr(incident.victim_work_experience, 'value') else incident.victim_work_experience,
            injury_type=incident.injury_type.value if incident.injury_type and hasattr(incident.injury_type, 'value') else incident.injury_type,
            diagnosis=incident.diagnosis,
            description=incident.description,
            investigation_status=incident.investigation_status.value if hasattr(incident.investigation_status, 'value') else incident.investigation_status,
            work_type=incident.work_type,
            equipment=incident.equipment,
            safety_responsible_person=incident.safety_responsible_person,
            weather_conditions=incident.weather_conditions,
            victim_count=incident.victim_count,
            fatality_count=incident.fatality_count,
            safety_training_completed=incident.safety_training_completed,
            is_recurrent=incident.is_recurrent,
            regulatory_compliant=incident.regulatory_compliant,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )


class PaginatedIncidentsResponseSchema(BaseModel):
    """Схема ответа списка инцидентов с пагинацией"""
    items: list[IncidentResponseSchema]
    total: int
    limit: int
    offset: int


class RecommendationResponseSchema(BaseModel):
    """Схема ответа рекомендации"""
    id: UUID
    recommendation_text: str
    priority: str
    status: str
    legal_references: list[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class StatisticsResponseSchema(BaseModel):
    """Схема ответа статистики"""
    total_count: int
    by_classification: dict[str, int]
    by_injury_type: dict[str, int]
    total_victims: int
    total_fatalities: int


class HeatmapResponseSchema(BaseModel):
    """Схема ответа тепловой карты"""
    regional_distribution: dict[str, int]


class AnalyticsSummaryResponseSchema(BaseModel):
    """Схема полной аналитической сводки"""
    total_incidents: int
    total_victims: int
    total_fatalities: int
    by_classification: dict[str, int]
    by_injury_type: dict[str, int]
    by_region: dict[str, int]
    by_company: dict[str, int]
    by_month: dict[str, int]


class ImportJournalResponseSchema(BaseModel):
    """Схема ответа импорта журнала"""
    processed: int
    created: int
    updated: int
    adopted_acts: int = 0
    warning: Optional[str] = None


class ImportJournalFileResultSchema(BaseModel):
    """Результат импорта одного файла из пакета (по file_id)"""
    file_id: UUID
    processed: int
    created: int
    updated: int
    adopted_acts: int = 0
    warning: Optional[str] = None
    error: Optional[str] = None


class ImportJournalBatchResponseSchema(BaseModel):
    """Схема ответа пакетного импорта журналов"""
    total_files: int
    successful_files: int
    failed_files: int
    total_processed: int
    total_created: int
    total_updated: int
    files: list[ImportJournalFileResultSchema]
