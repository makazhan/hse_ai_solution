"""Pydantic-схемы запроса и ответа для аналитического отчёта."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from src.application.exceptions.incidents import InvalidCompanyException
from src.domain.enums.incidents import Company, IncidentClassification, InjuryType


class GenerateReportRequestSchema(BaseModel):
    """Запрос генерации отчёта."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    region: Optional[str] = None
    companies: Optional[list[str]] = None
    classification: Optional[str] = None
    injury_type: Optional[str] = None
    include_ai_analysis: bool = True

    @field_validator('companies')
    @classmethod
    def validate_companies(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Валидация списка компаний против перечисления Company."""
        if v is None:
            return v
        valid_values = {c.value for c in Company}
        for company in v:
            if company not in valid_values:
                raise InvalidCompanyException(company=company)
        return v

    @field_validator('classification')
    @classmethod
    def validate_classification(cls, v: Optional[str]) -> Optional[str]:
        """Валидация классификации инцидента."""
        if v is None:
            return v
        try:
            IncidentClassification(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимая классификация: {v}. Допустимые: {', '.join(c.value for c in IncidentClassification)}")

    @field_validator('injury_type')
    @classmethod
    def validate_injury_type(cls, v: Optional[str]) -> Optional[str]:
        """Валидация типа травмы."""
        if v is None:
            return v
        try:
            InjuryType(v)
            return v
        except ValueError:
            raise ValueError(f"Недопустимый тип травмы: {v}. Допустимые: {', '.join(i.value for i in InjuryType)}")

    @model_validator(mode='after')
    def validate_date_range(self) -> 'GenerateReportRequestSchema':
        """Проверка: date_from не должен быть позже date_to."""
        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValueError("date_from не может быть позже date_to")
        return self


class RiskItemSchema(BaseModel):
    risk_type: str
    severity: str
    description: str
    affected_entities: list[str] = []


class RecurrencePatternSchema(BaseModel):
    pattern_description: str
    frequency: int
    affected_companies: list[str] = []
    affected_regions: list[str] = []


class RecommendationItemSchema(BaseModel):
    priority: str
    recommendation: str
    rationale: str
    target_entities: list[str] = []


class CauseCategorySchema(BaseModel):
    category: str
    count: int
    analysis: str = ""


class AnalyticalReportResponseSchema(BaseModel):
    """Ответ с аналитическим отчётом."""
    summary_narrative: str
    key_findings: list[str]
    cause_analysis: str
    top_cause_categories: list[CauseCategorySchema]
    recurrence_patterns: list[RecurrencePatternSchema]
    risk_assessment: list[RiskItemSchema]
    overall_risk_level: str
    recommendations: list[RecommendationItemSchema]
    immediate_actions: list[str]
    report_language: str = "ru"
    confidence_note: Optional[str] = None
    raw_summary: Optional[dict] = None
