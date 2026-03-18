import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class EnquiryActFilters:
    """Фильтры для запроса актов расследования.

    Перечислимые поля принимают строки — валидация выполняется
    на уровне Pydantic-схемы в presentation.
    """
    act_type: Optional[str] = None
    link_status: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    victim_name: Optional[str] = None
    company_name: Optional[str] = None
    companies: Optional[list[str]] = None
    region: Optional[str] = None
    regions: Optional[list[str]] = None
    language: Optional[str] = None
    incident_id: Optional[str] = None
    # Теги для фильтрации по классификации паттернов
    cause_category: Optional[str] = None
    violation_type: Optional[str] = None
    industry_tag: Optional[str] = None
