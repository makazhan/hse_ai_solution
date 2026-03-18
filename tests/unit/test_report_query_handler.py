"""Тесты GenerateAnalyticalReportQueryHandler — сборка контекста, stub path, маппинг LLM."""
import pytest
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from src.application.filters.incidents import IncidentFilters
from src.application.queries.reports import (
    AnalyticalReport,
    CauseCategoryDTO,
    GenerateAnalyticalReportQuery,
    GenerateAnalyticalReportQueryHandler,
    RecurrencePatternDTO,
    RecommendationItemDTO,
    RiskItemDTO,
)


def _make_incident(**overrides):
    """Фабрика мок-инцидента с дефолтными полями."""
    defaults = {
        "id": uuid4(),
        "incident_date": date(2024, 6, 15),
        "company": MagicMock(value="АО «Казахтелеком»"),
        "region": MagicMock(value="Алматы"),
        "classification": MagicMock(value="Несчастный случай"),
        "injury_type": MagicMock(value="Травма относится к тяжелым"),
        "description": "Описание инцидента",
        "preliminary_causes": "Предварительные причины",
        "root_causes": "Коренные причины",
        "victim_position": "Инженер",
        "work_type": "Монтаж",
        "equipment": "Кран",
        "safety_training_completed": True,
        "is_recurrent": False,
        "victim_count": 1,
        "fatality_count": 0,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


EMPTY_SUMMARY = {
    "total_incidents": 0,
    "total_victims": 0,
    "total_fatalities": 0,
    "by_classification": {},
    "by_injury_type": {},
    "by_region": {},
    "by_company": {},
    "by_month": {},
}

SAMPLE_SUMMARY = {
    "total_incidents": 5,
    "total_victims": 7,
    "total_fatalities": 1,
    "by_classification": {"Несчастный случай": 5},
    "by_injury_type": {"Травма относится к тяжелым": 3, "Смертельный исход": 1},
    "by_region": {"Алматы": 3, "Астана": 2},
    "by_company": {"АО «Казахтелеком»": 5},
    "by_month": {"2024-06": 5},
}

SAMPLE_LLM_RESULT = {
    "summary_narrative": "Аналитическая сводка.",
    "key_findings": ["Вывод 1", "Вывод 2"],
    "cause_analysis": "Анализ причин.",
    "top_cause_categories": [
        {"category": "Организационные", "count": 3, "analysis": "Основная причина"},
    ],
    "recurrence_patterns": [
        {
            "pattern_description": "Повторные НС",
            "frequency": 2,
            "affected_companies": ["АО «Казахтелеком»"],
            "affected_regions": ["Алматы"],
        },
    ],
    "risk_assessment": [
        {
            "risk_type": "финансовый",
            "severity": "высокий",
            "description": "Штрафы",
            "affected_entities": ["АО «Казахтелеком»"],
        },
    ],
    "overall_risk_level": "высокий",
    "recommendations": [
        {
            "priority": "высокий",
            "recommendation": "Провести обучение",
            "rationale": "3 из 5 — организационные",
            "target_entities": ["АО «Казахтелеком»"],
        },
    ],
    "immediate_actions": ["Остановить работы"],
    "confidence_note": None,
}


def _build_handler(
    mocker,
    summary=None,
    incidents=None,
    cause_categories=None,
    violation_types=None,
    act_summaries=None,
    llm_result=None,
    llm_service_none=False,
):
    """Собрать handler с замоканными зависимостями."""
    inc_repo = mocker.AsyncMock()
    inc_repo.get_aggregated_summary.return_value = summary or SAMPLE_SUMMARY
    inc_repo.get_filtered.return_value = incidents if incidents is not None else [_make_incident()]

    act_repo = mocker.AsyncMock()
    act_repo.get_tag_patterns.side_effect = [
        cause_categories or [("Организационные", 3)],
        violation_types or [("Нарушение ТБ", 2)],
    ]
    act_repo.get_linked_act_summaries.return_value = act_summaries or []

    llm_service = None
    if not llm_service_none:
        llm_service = mocker.AsyncMock()
        llm_service.generate_report.return_value = llm_result if llm_result is not None else SAMPLE_LLM_RESULT

    handler = GenerateAnalyticalReportQueryHandler(
        incident_repository=inc_repo,
        enquiry_act_repository=act_repo,
        llm_report_service=llm_service,
    )
    return handler, inc_repo, act_repo, llm_service


class TestStubPaths:
    """Проверка путей, при которых LLM не вызывается."""

    @pytest.mark.asyncio
    async def test_empty_dataset_returns_stub(self, mocker):
        """При 0 инцидентов — стаб без LLM-вызова, фаза 2 не выполняется."""
        handler, _, act_repo, llm_svc = _build_handler(mocker, summary=EMPTY_SUMMARY)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        result = await handler.handle(query)

        assert result.confidence_note == "Нет инцидентов, соответствующих заданным фильтрам."
        assert "AI-анализ не выполнен" in result.key_findings[0]
        llm_svc.generate_report.assert_not_called()
        act_repo.get_tag_patterns.assert_not_called()

    @pytest.mark.asyncio
    async def test_include_ai_false_returns_stub(self, mocker):
        """include_ai_analysis=False — стаб."""
        handler, _, _, llm_svc = _build_handler(mocker)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=False,
        )

        result = await handler.handle(query)

        assert "AI-анализ не был выполнен" in result.confidence_note
        llm_svc.generate_report.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_llm_service_returns_stub(self, mocker):
        """llm_report_service=None — стаб."""
        handler, _, _, _ = _build_handler(mocker, llm_service_none=True)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        result = await handler.handle(query)

        assert "AI-анализ не был выполнен" in result.confidence_note

    @pytest.mark.asyncio
    async def test_llm_returns_empty_dict(self, mocker):
        """LLM вернул {} — стаб."""
        handler, _, _, llm_svc = _build_handler(mocker, llm_result={})
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        result = await handler.handle(query)

        assert "AI-анализ не был выполнен" in result.confidence_note
        llm_svc.generate_report.assert_called_once()


class TestContextAssembly:
    """Проверка корректной сборки контекста для LLM."""

    @pytest.mark.asyncio
    async def test_context_contains_all_blocks(self, mocker):
        """Контекст содержит все 5 блоков данных."""
        handler, _, _, llm_svc = _build_handler(mocker)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        llm_svc.generate_report.assert_called_once()
        context = llm_svc.generate_report.call_args[0][0]
        assert "summary" in context
        assert "incidents_sample" in context
        assert "cause_patterns" in context
        assert "act_summaries" in context
        assert "recurrence_data" in context

    @pytest.mark.asyncio
    async def test_incidents_sample_limited_to_30(self, mocker):
        """Выборка инцидентов ограничена 30 элементами."""
        incidents = [_make_incident() for _ in range(50)]
        handler, _, _, llm_svc = _build_handler(mocker, incidents=incidents)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        context = llm_svc.generate_report.call_args[0][0]
        assert len(context["incidents_sample"]) == 30

    @pytest.mark.asyncio
    async def test_description_truncated(self, mocker):
        """Описание инцидента обрезается до 300 символов."""
        long_desc = "А" * 500
        incidents = [_make_incident(description=long_desc)]
        handler, _, _, llm_svc = _build_handler(mocker, incidents=incidents)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        context = llm_svc.generate_report.call_args[0][0]
        assert len(context["incidents_sample"][0]["description"]) == 300

    @pytest.mark.asyncio
    async def test_recurrence_data_computed(self, mocker):
        """Повторяемость корректно подсчитана."""
        incidents = [
            _make_incident(is_recurrent=True),
            _make_incident(is_recurrent=True),
            _make_incident(is_recurrent=False),
        ]
        handler, _, _, llm_svc = _build_handler(mocker, incidents=incidents)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        context = llm_svc.generate_report.call_args[0][0]
        assert context["recurrence_data"]["АО «Казахтелеком»"] == 2

    @pytest.mark.asyncio
    async def test_act_summaries_limited_to_20(self, mocker):
        """Резюме актов ограничены 20 элементами."""
        summaries = [{"ai_summary": f"summary {i}"} for i in range(30)]
        handler, _, _, llm_svc = _build_handler(mocker, act_summaries=summaries)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        context = llm_svc.generate_report.call_args[0][0]
        assert len(context["act_summaries"]) == 20


class TestLLMResultMapping:
    """Проверка маппинга LLM-ответа в типизированный AnalyticalReport."""

    @pytest.mark.asyncio
    async def test_full_llm_result_mapped(self, mocker):
        """Полный LLM-ответ корректно маппится в AnalyticalReport."""
        handler, _, _, _ = _build_handler(mocker, llm_result=SAMPLE_LLM_RESULT)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        result = await handler.handle(query)

        assert isinstance(result, AnalyticalReport)
        assert result.summary_narrative == "Аналитическая сводка."
        assert len(result.key_findings) == 2
        assert result.overall_risk_level == "высокий"
        assert result.raw_summary == SAMPLE_SUMMARY

    @pytest.mark.asyncio
    async def test_typed_dtos_in_result(self, mocker):
        """Результат содержит типизированные DTO, а не dict."""
        handler, _, _, _ = _build_handler(mocker, llm_result=SAMPLE_LLM_RESULT)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        result = await handler.handle(query)

        assert isinstance(result.top_cause_categories[0], CauseCategoryDTO)
        assert result.top_cause_categories[0].category == "Организационные"

        assert isinstance(result.recurrence_patterns[0], RecurrencePatternDTO)
        assert result.recurrence_patterns[0].frequency == 2

        assert isinstance(result.risk_assessment[0], RiskItemDTO)
        assert result.risk_assessment[0].risk_type == "финансовый"

        assert isinstance(result.recommendations[0], RecommendationItemDTO)
        assert result.recommendations[0].priority == "высокий"

    @pytest.mark.asyncio
    async def test_parallel_db_queries(self, mocker):
        """Фаза 1 — сводка + инциденты; фаза 2 — акты + теги (по incident_ids)."""
        handler, inc_repo, act_repo, _ = _build_handler(mocker)
        query = GenerateAnalyticalReportQuery(
            filters=IncidentFilters(),
            include_ai_analysis=True,
        )

        await handler.handle(query)

        # Фаза 1
        inc_repo.get_aggregated_summary.assert_called_once()
        inc_repo.get_filtered.assert_called_once()
        # Фаза 2: теги фильтруются по incident_ids
        assert act_repo.get_tag_patterns.call_count == 2
        for call in act_repo.get_tag_patterns.call_args_list:
            assert "incident_ids" in call.kwargs
        act_repo.get_linked_act_summaries.assert_called_once()
