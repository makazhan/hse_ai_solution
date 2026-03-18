"""Pydantic-схема для валидации JSON-ответа LLM при генерации аналитического отчёта."""
from typing import Optional

from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    """Единичная оценка риска."""
    risk_type: str = Field(description="финансовый / регуляторный / репутационный")
    severity: str = Field(description="высокий / средний / низкий")
    description: str = Field(description="Описание риска с привязкой к данным")
    affected_entities: list[str] = Field(
        default_factory=list,
        description="Затронутые компании / регионы",
    )


class RecurrencePattern(BaseModel):
    """Выявленный паттерн повторяемости."""
    pattern_description: str
    frequency: int = Field(description="Количество повторений")
    affected_companies: list[str] = Field(default_factory=list)
    affected_regions: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    """Рекомендация ИИ-эксперта."""
    priority: str = Field(description="высокий / средний / низкий")
    recommendation: str
    rationale: str = Field(description="Обоснование на основе данных")
    target_entities: list[str] = Field(
        default_factory=list,
        description="Компании/регионы, к которым применима",
    )


class CauseCategoryItem(BaseModel):
    """Категория причин с анализом."""
    category: str
    count: int
    analysis: str = ""


class AnalyticalReportLLMResponse(BaseModel):
    """Полная схема ответа LLM для аналитического отчёта."""
    summary_narrative: str = Field(
        description="Текстовая интерпретация сводной статистики (2-4 абзаца)",
    )
    key_findings: list[str] = Field(
        description="Ключевые выводы (3-7 пунктов)",
    )
    cause_analysis: str = Field(
        description="Анализ основных и непосредственных причин (2-4 абзаца)",
    )
    top_cause_categories: list[CauseCategoryItem] = Field(
        default_factory=list,
        description="Топ категорий причин с пояснениями",
    )
    recurrence_patterns: list[RecurrencePattern] = Field(
        default_factory=list,
        description="Выявленные паттерны повторяемости",
    )
    risk_assessment: list[RiskItem] = Field(
        default_factory=list,
        description="Оценка рисков по 3 типам",
    )
    overall_risk_level: str = Field(
        default="не определён",
        description="Общий уровень риска: высокий / средний / низкий",
    )
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="Рекомендации эксперта (5-10 пунктов)",
    )
    immediate_actions: list[str] = Field(
        default_factory=list,
        description="Первоочередные действия (2-5 пунктов)",
    )
    report_language: str = Field(default="ru")
    confidence_note: Optional[str] = Field(
        default=None,
        description="Примечание о достоверности при недостатке данных",
    )
