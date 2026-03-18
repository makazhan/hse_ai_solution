"""Pydantic-схема для валидации JSON-ответа LLM при извлечении данных из акта."""
import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ResponsiblePersonSchema(BaseModel):
    """Ответственное лицо, указанное в акте."""
    name: Optional[str] = None
    position: Optional[str] = None
    violation: Optional[str] = None


class CorrectiveMeasureSchema(BaseModel):
    """Корректирующее мероприятие из акта."""
    measure: Optional[str] = None
    deadline: Optional[str] = None
    responsible: Optional[str] = None


_ACT_TYPE_ALIASES: dict[str, str] = {
    "внутреннее расследование": "Внутреннее расследование",
    "служебное расследование": "Внутреннее расследование",
    "специальное расследование": "Специальное расследование",
}


class EnquiryActExtractionResult(BaseModel):
    """Результат LLM-извлечения из текста акта расследования.

    Все поля Optional — частичное извлечение допустимо.
    """
    # Метаданные документа
    act_type: Optional[str] = None

    @field_validator("act_type", mode="before")
    @classmethod
    def _normalize_act_type(cls, v: object) -> object:
        """Нормализация act_type: LLM может вернуть синоним вместо точного значения."""
        if isinstance(v, str):
            return _ACT_TYPE_ALIASES.get(v.strip().lower(), v.strip())
        return v
    act_date: Optional[datetime.date] = None
    act_number: Optional[str] = None
    language: Optional[str] = None

    # Комиссия
    commission_chairman: Optional[str] = None
    commission_members: Optional[list[str]] = None
    investigation_period: Optional[str] = None

    # Поля для авто-матчинга
    incident_date_from_act: Optional[datetime.date] = None
    victim_name_from_act: Optional[str] = None
    company_name_from_act: Optional[str] = None
    region_from_act: Optional[str] = None

    # Сведения о пострадавшем
    victim_name: Optional[str] = None
    victim_birth_date: Optional[datetime.date] = None
    victim_position: Optional[str] = None
    victim_experience: Optional[str] = None
    victim_training_dates: Optional[str] = None
    injury_severity: Optional[str] = None
    victim_dependents: Optional[str] = None

    @field_validator("victim_birth_date", mode="before")
    @classmethod
    def _coerce_birth_date(cls, v: object) -> object:
        """LLM может вернуть только год ('1994') — приводим к 1 января."""
        if isinstance(v, str) and len(v) == 4 and v.isdigit():
            return datetime.date(int(v), 1, 1)
        return v

    @field_validator("victim_training_dates", mode="before")
    @classmethod
    def _coerce_training_dates(cls, v: object) -> object:
        """LLM может вернуть список дат — объединяем в строку."""
        if isinstance(v, list):
            return ", ".join(str(item) for item in v)
        return v

    # Предприятие
    company_name: Optional[str] = None
    company_bin: Optional[str] = None
    workplace_description: Optional[str] = None

    # Обстоятельства и причины
    circumstances: Optional[str] = None
    root_causes: Optional[str] = None
    immediate_causes: Optional[str] = None
    state_classifier_codes: Optional[list[str]] = None
    investigation_method: Optional[str] = None

    # Нарушения НПА
    legal_violations: Optional[list[str]] = None

    # Ответственные лица
    responsible_persons: Optional[list[ResponsiblePersonSchema]] = None

    # Мероприятия
    corrective_measures: Optional[list[CorrectiveMeasureSchema]] = None

    # Выводы
    work_related: Optional[bool] = None
    employer_fault_pct: Optional[int] = None
    worker_fault_pct: Optional[int] = None
    conclusions: Optional[str] = None

    # AI-теги
    ai_summary: Optional[str] = None
    ai_risk_factors: Optional[list[str]] = None
    cause_categories: Optional[list[str]] = None
    violation_types: Optional[list[str]] = None
    industry_tags: Optional[list[str]] = None
