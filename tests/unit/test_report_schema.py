"""Тесты Pydantic-схемы AnalyticalReportLLMResponse."""
import json

import pytest

from src.infrastructure.llm.report_schema import (
    AnalyticalReportLLMResponse,
    CauseCategoryItem,
    RecurrencePattern,
    RecommendationItem,
    RiskItem,
)


FULL_REPORT_DATA = {
    "summary_narrative": "Общая сводка.",
    "key_findings": ["Вывод 1", "Вывод 2", "Вывод 3"],
    "cause_analysis": "Анализ причин.",
    "top_cause_categories": [
        {"category": "Организационные", "count": 5, "analysis": "Лидирует"},
    ],
    "recurrence_patterns": [
        {
            "pattern_description": "Повтор",
            "frequency": 3,
            "affected_companies": ["АО «Казахтелеком»"],
            "affected_regions": ["Алматы"],
        },
    ],
    "risk_assessment": [
        {
            "risk_type": "финансовый",
            "severity": "высокий",
            "description": "Штрафы до 500 МРП",
            "affected_entities": ["АО «Казахтелеком»"],
        },
    ],
    "overall_risk_level": "высокий",
    "recommendations": [
        {
            "priority": "высокий",
            "recommendation": "Провести аудит",
            "rationale": "5 организационных причин",
            "target_entities": ["АО «Казахтелеком»"],
        },
    ],
    "immediate_actions": ["Остановить работы", "Уведомить Госинспекцию"],
    "report_language": "ru",
    "confidence_note": None,
}


class TestAnalyticalReportLLMResponse:

    def test_full_data(self):
        """Полный набор данных — успешная валидация."""
        result = AnalyticalReportLLMResponse.model_validate(FULL_REPORT_DATA)

        assert result.summary_narrative == "Общая сводка."
        assert len(result.key_findings) == 3
        assert result.overall_risk_level == "высокий"
        assert len(result.top_cause_categories) == 1
        assert isinstance(result.top_cause_categories[0], CauseCategoryItem)
        assert len(result.risk_assessment) == 1
        assert isinstance(result.risk_assessment[0], RiskItem)
        assert len(result.recommendations) == 1
        assert isinstance(result.recommendations[0], RecommendationItem)
        assert len(result.recurrence_patterns) == 1
        assert isinstance(result.recurrence_patterns[0], RecurrencePattern)

    def test_minimal_data(self):
        """Минимальный набор — только обязательные поля."""
        data = {
            "summary_narrative": "Краткая сводка.",
            "key_findings": ["Вывод"],
            "cause_analysis": "Причины.",
        }
        result = AnalyticalReportLLMResponse.model_validate(data)

        assert result.summary_narrative == "Краткая сводка."
        assert result.top_cause_categories == []
        assert result.recurrence_patterns == []
        assert result.risk_assessment == []
        assert result.recommendations == []
        assert result.immediate_actions == []
        assert result.overall_risk_level == "не определён"
        assert result.confidence_note is None

    def test_partial_data_with_defaults(self):
        """Частичные данные — default_factory заполняет пустые списки."""
        data = {
            "summary_narrative": "Текст.",
            "key_findings": ["Один вывод"],
            "cause_analysis": "Причины.",
            "overall_risk_level": "средний",
            "immediate_actions": ["Действие 1"],
        }
        result = AnalyticalReportLLMResponse.model_validate(data)

        assert result.overall_risk_level == "средний"
        assert result.immediate_actions == ["Действие 1"]
        assert result.top_cause_categories == []
        assert result.risk_assessment == []

    def test_from_json_string(self):
        """Валидация из JSON-строки (как приходит от LLM)."""
        json_str = json.dumps(FULL_REPORT_DATA, ensure_ascii=False)
        result = AnalyticalReportLLMResponse.model_validate_json(json_str)

        assert result.summary_narrative == "Общая сводка."
        assert len(result.recommendations) == 1

    def test_model_dump_roundtrip(self):
        """model_dump() -> model_validate() — roundtrip."""
        original = AnalyticalReportLLMResponse.model_validate(FULL_REPORT_DATA)
        dumped = original.model_dump()
        restored = AnalyticalReportLLMResponse.model_validate(dumped)

        assert restored.summary_narrative == original.summary_narrative
        assert len(restored.risk_assessment) == len(original.risk_assessment)

    def test_missing_required_fields_raises(self):
        """Отсутствие обязательных полей — ValidationError."""
        with pytest.raises(Exception):
            AnalyticalReportLLMResponse.model_validate({})

    def test_extra_fields_ignored(self):
        """Лишние поля от LLM — не ломают валидацию."""
        data = {
            **FULL_REPORT_DATA,
            "extra_field": "ignored",
            "another_one": 42,
        }
        result = AnalyticalReportLLMResponse.model_validate(data)
        assert result.summary_narrative == "Общая сводка."


class TestRiskItem:
    def test_full(self):
        r = RiskItem(risk_type="финансовый", severity="высокий", description="Штрафы")
        assert r.risk_type == "финансовый"
        assert r.affected_entities == []

    def test_with_entities(self):
        r = RiskItem(
            risk_type="регуляторный",
            severity="средний",
            description="Проверки",
            affected_entities=["АО «Казахтелеком»"],
        )
        assert len(r.affected_entities) == 1


class TestRecommendationItem:
    def test_full(self):
        r = RecommendationItem(
            priority="высокий",
            recommendation="Провести обучение",
            rationale="Обоснование",
        )
        assert r.priority == "высокий"
        assert r.target_entities == []


class TestRecurrencePattern:
    def test_full(self):
        p = RecurrencePattern(
            pattern_description="Повтор падений",
            frequency=5,
            affected_companies=["АО «Казахтелеком»"],
        )
        assert p.frequency == 5
        assert p.affected_regions == []
