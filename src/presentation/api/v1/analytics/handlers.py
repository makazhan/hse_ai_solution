import datetime as _dt
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from punq import Container

from src.domain.entities.users import UserEntity
from src.presentation.api.v1.auth import get_current_user

from src.application.queries.incidents import (
    GetIncidentStatisticsQuery,
    GetRegionalHeatmapQuery,
    GetAggregatedSummaryQuery,
)
from src.application.queries.reports import GenerateAnalyticalReportQuery
from src.application.filters.incidents import IncidentFilters
from src.application.mediator.base import Mediator
from src.infrastructure.di.containers import init_container
from src.presentation.api.v1.incidents.schemas import (
    StatisticsResponseSchema,
    HeatmapResponseSchema,
    AnalyticsSummaryResponseSchema,
    IncidentFiltersSchema,
)
from src.presentation.api.v1.analytics.report_schemas import (
    GenerateReportRequestSchema,
    AnalyticalReportResponseSchema,
)
from src.infrastructure.reports.docx_builder import build_report_docx


router = APIRouter(prefix='/analytics', tags=['analytics'])


@router.get('/dashboard', response_model=StatisticsResponseSchema)
async def get_dashboard_handler(
    company_name: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> StatisticsResponseSchema:
    """Получить данные для дашборда"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetIncidentStatisticsQuery(
        company_name=company_name,
        date_from=date_from,
        date_to=date_to,
    )
    stats = await mediator.handle_query(query)

    return StatisticsResponseSchema(
        total_count=stats.total_count,
        by_classification=stats.by_classification,
        by_injury_type=stats.by_injury_type,
        total_victims=stats.total_victims,
        total_fatalities=stats.total_fatalities,
    )


@router.get('/heatmap', response_model=HeatmapResponseSchema)
async def get_heatmap_handler(
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> HeatmapResponseSchema:
    """Получить данные тепловой карты Казахстана"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetRegionalHeatmapQuery()
    distribution = await mediator.handle_query(query)

    return HeatmapResponseSchema(regional_distribution=distribution)


@router.get('/summary', response_model=AnalyticsSummaryResponseSchema)
async def get_summary_handler(
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
    filters: IncidentFiltersSchema = Depends(),
) -> AnalyticsSummaryResponseSchema:
    """Получить полную аналитическую сводку с фильтрами"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetAggregatedSummaryQuery(
        filters=IncidentFilters(**filters.model_dump()),
    )
    summary = await mediator.handle_query(query)

    return AnalyticsSummaryResponseSchema(**summary)


@router.post('/report', response_model=AnalyticalReportResponseSchema)
async def generate_report_handler(
    body: GenerateReportRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> AnalyticalReportResponseSchema:
    """Сгенерировать аналитический отчёт по инцидентам ТБ.

    Включает AI-анализ причин, оценку рисков и рекомендации.
    """
    mediator: Mediator = container.resolve(Mediator)

    filters = IncidentFilters(
        date_from=body.date_from,
        date_to=body.date_to,
        region=body.region,
        companies=body.companies,
        classification=body.classification,
        injury_type=body.injury_type,
    )

    query = GenerateAnalyticalReportQuery(
        filters=filters,
        include_ai_analysis=body.include_ai_analysis,
    )
    report = await mediator.handle_query(query)

    return AnalyticalReportResponseSchema(
        summary_narrative=report.summary_narrative,
        key_findings=report.key_findings,
        cause_analysis=report.cause_analysis,
        top_cause_categories=[asdict(c) for c in report.top_cause_categories],
        recurrence_patterns=[asdict(p) for p in report.recurrence_patterns],
        risk_assessment=[asdict(r) for r in report.risk_assessment],
        overall_risk_level=report.overall_risk_level,
        recommendations=[asdict(r) for r in report.recommendations],
        immediate_actions=report.immediate_actions,
        report_language=report.report_language,
        confidence_note=report.confidence_note,
        raw_summary=report.raw_summary,
    )


@router.post('/report/docx')
async def export_report_docx_handler(
    body: AnalyticalReportResponseSchema,
    _user: UserEntity = Depends(get_current_user),
) -> StreamingResponse:
    """Экспорт готового аналитического отчёта в DOCX."""
    buf = build_report_docx(body.model_dump())
    today = _dt.date.today().strftime("%Y-%m-%d")
    filename = f"otchet_tb_{today}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
