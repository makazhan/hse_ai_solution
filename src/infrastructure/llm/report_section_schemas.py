"""Pydantic-схемы для валидации секционных ответов LLM."""
from pydantic import BaseModel, Field

from src.infrastructure.llm.report_schema import (
    CauseCategoryItem,
    RecurrencePattern,
    RecommendationItem,
    RiskItem,
)


class CausesSectionResponse(BaseModel):
    """Секция 2: анализ причин и повторяемости."""
    cause_analysis: str = Field(
        description="Анализ причин (2-4 абзаца)",
    )
    top_cause_categories: list[CauseCategoryItem] = Field(
        default_factory=list,
        description="Топ категорий причин",
    )
    recurrence_patterns: list[RecurrencePattern] = Field(
        default_factory=list,
        description="Паттерны повторяемости",
    )


class RisksSectionResponse(BaseModel):
    """Секция 3: оценка рисков."""
    risk_assessment: list[RiskItem] = Field(
        default_factory=list,
        description="Оценка рисков (3 типа: финансовый/регуляторный/репутационный)",
    )
    overall_risk_level: str = Field(
        default="не определён",
        description="Общий уровень риска",
    )


class RecommendationsSectionResponse(BaseModel):
    """Секция 4: рекомендации."""
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="Рекомендации (5-10 пунктов)",
    )
    immediate_actions: list[str] = Field(
        default_factory=list,
        description="Первоочередные действия (2-5 пунктов)",
    )
