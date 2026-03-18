import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class IncidentFilters:
    """Фильтры для запроса инцидентов.

    Перечислимые поля (region, company, ...) принимают строки —
    валидация значений выполняется на уровне Pydantic-схемы в presentation.
    """
    # Дата (период)
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None

    # Перечислимые фильтры (строковые значения enum)
    region: Optional[str] = None
    company: Optional[str] = None
    companies: Optional[list[str]] = None
    regions: Optional[list[str]] = None
    classification: Optional[str] = None
    injury_type: Optional[str] = None
    investigation_status: Optional[str] = None
    investigation_results: Optional[str] = None
    work_experience: Optional[str] = None

    # Текстовый поиск (ILIKE)
    location: Optional[str] = None
    description: Optional[str] = None
    victim_name: Optional[str] = None
    victim_position: Optional[str] = None
    dzo: Optional[str] = None

    # Время суток
    time_from: Optional[datetime.time] = None
    time_to: Optional[datetime.time] = None

    # Поиск по причинам (preliminary_causes / main_causes_from_report)
    cause_search: Optional[str] = None

    # Фаза A: текстовый поиск (ILIKE)
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # Фаза B: диапазоны (мин/макс)
    victim_count_min: Optional[int] = None
    victim_count_max: Optional[int] = None
    fatality_count_min: Optional[int] = None
    fatality_count_max: Optional[int] = None

    # Фаза C: булевые
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None

    # Фаза B: субзапрос по рекомендациям
    recommendation_status: Optional[str] = None