from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.application.queries.base import BaseQuery, BaseQueryHandler
from src.application.filters.incidents import IncidentFilters
from src.application.filters.common import PaginationIn
from src.application.interfaces.repositories.incidents import (
    BaseIncidentRepository,
    BaseEnquiryActRepository,
    BaseRecommendationRepository,
    IncidentStatistics,
)
from src.domain.entities.incidents import Incident, EnquiryAct, Recommendation


@dataclass(frozen=True)
class GetIncidentsQuery(BaseQuery):
    """Запрос списка инцидентов с фильтрацией"""
    filters: IncidentFilters
    pagination: PaginationIn


@dataclass(frozen=True)
class GetIncidentsQueryHandler(BaseQueryHandler[GetIncidentsQuery, list[Incident]]):
    """Обработчик получения списка инцидентов"""
    incident_repository: BaseIncidentRepository
    
    async def handle(self, query: GetIncidentsQuery) -> list[Incident]:
        """Получение отфильтрованного списка инцидентов"""
        return await self.incident_repository.get_filtered(
            filters=query.filters,
            pagination=query.pagination,
        )


@dataclass(frozen=True)
class GetIncidentCountQuery(BaseQuery):
    """Запрос количества инцидентов по фильтрам"""
    filters: IncidentFilters


@dataclass(frozen=True)
class GetIncidentCountQueryHandler(BaseQueryHandler[GetIncidentCountQuery, int]):
    """Обработчик подсчета инцидентов"""
    incident_repository: BaseIncidentRepository

    async def handle(self, query: GetIncidentCountQuery) -> int:
        return await self.incident_repository.get_count(query.filters)


@dataclass(frozen=True)
class GetIncidentByIdQuery(BaseQuery):
    """Запрос детальной информации по инциденту"""
    incident_id: UUID


@dataclass(frozen=True)
class GetIncidentByIdQueryHandler(BaseQueryHandler[GetIncidentByIdQuery, Optional[Incident]]):
    """Обработчик получения инцидента по ID"""
    incident_repository: BaseIncidentRepository
    
    async def handle(self, query: GetIncidentByIdQuery) -> Optional[Incident]:
        """Получение инцидента по ID"""
        return await self.incident_repository.get_by_id(query.incident_id)


@dataclass(frozen=True)
class GetIncidentStatisticsQuery(BaseQuery):
    """Запрос статистики по инцидентам"""
    company_name: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass(frozen=True)
class GetIncidentStatisticsQueryHandler(
    BaseQueryHandler[GetIncidentStatisticsQuery, IncidentStatistics]
):
    """Обработчик получения статистики"""
    incident_repository: BaseIncidentRepository
    
    async def handle(self, query: GetIncidentStatisticsQuery) -> IncidentStatistics:
        """Получение статистики по инцидентам"""
        return await self.incident_repository.get_statistics(
            company_name=query.company_name,
            date_from=query.date_from,
            date_to=query.date_to,
        )


@dataclass(frozen=True)
class GetRegionalHeatmapQuery(BaseQuery):
    """Запрос данных для тепловой карты"""
    pass


@dataclass(frozen=True)
class GetRegionalHeatmapQueryHandler(
    BaseQueryHandler[GetRegionalHeatmapQuery, dict[str, int]]
):
    """Обработчик получения данных тепловой карты"""
    incident_repository: BaseIncidentRepository
    
    async def handle(self, query: GetRegionalHeatmapQuery) -> dict[str, int]:
        """Получение распределения инцидентов по регионам"""
        return await self.incident_repository.get_regional_distribution()


@dataclass(frozen=True)
class GetAggregatedSummaryQuery(BaseQuery):
    """Запрос полной аналитической сводки"""
    filters: IncidentFilters


@dataclass(frozen=True)
class GetAggregatedSummaryQueryHandler(
    BaseQueryHandler[GetAggregatedSummaryQuery, dict]
):
    """Обработчик полной аналитической сводки"""
    incident_repository: BaseIncidentRepository

    async def handle(self, query: GetAggregatedSummaryQuery) -> dict:
        return await self.incident_repository.get_aggregated_summary(query.filters)


@dataclass(frozen=True)
class GetEnquiryActsByIncidentQuery(BaseQuery):
    """Запрос актов расследования по инциденту"""
    incident_id: UUID


@dataclass(frozen=True)
class GetEnquiryActsByIncidentQueryHandler(
    BaseQueryHandler[GetEnquiryActsByIncidentQuery, list[EnquiryAct]]
):
    """Обработчик получения актов расследования"""
    enquiry_act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetEnquiryActsByIncidentQuery) -> list[EnquiryAct]:
        """Получение актов расследования по инциденту"""
        return await self.enquiry_act_repository.get_by_incident_id(
            query.incident_id
        )


@dataclass(frozen=True)
class GetRecommendationsQuery(BaseQuery):
    """Запрос рекомендаций по инциденту"""
    incident_id: UUID


@dataclass(frozen=True)
class GetRecommendationsQueryHandler(
    BaseQueryHandler[GetRecommendationsQuery, list[Recommendation]]
):
    """Обработчик получения рекомендаций"""
    recommendation_repository: BaseRecommendationRepository

    async def handle(self, query: GetRecommendationsQuery) -> list[Recommendation]:
        """Получение рекомендаций по инциденту"""
        return await self.recommendation_repository.get_by_incident_id(
            query.incident_id
        )