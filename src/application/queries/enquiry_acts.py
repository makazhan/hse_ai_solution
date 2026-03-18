from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.application.queries.base import BaseQuery, BaseQueryHandler
from src.application.filters.enquiry_acts import EnquiryActFilters
from src.application.filters.common import PaginationIn
from src.application.interfaces.repositories.incidents import BaseEnquiryActRepository
from src.domain.entities.incidents import EnquiryAct


@dataclass(frozen=True)
class GetEnquiryActsQuery(BaseQuery):
    """Запрос списка актов с фильтрацией"""
    filters: EnquiryActFilters
    pagination: PaginationIn


@dataclass(frozen=True)
class GetEnquiryActsQueryHandler(BaseQueryHandler[GetEnquiryActsQuery, list[EnquiryAct]]):
    """Обработчик получения списка актов"""
    act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetEnquiryActsQuery) -> list[EnquiryAct]:
        return await self.act_repository.get_filtered(
            filters=query.filters,
            pagination=query.pagination,
        )


@dataclass(frozen=True)
class GetEnquiryActCountQuery(BaseQuery):
    """Запрос количества актов по фильтрам"""
    filters: EnquiryActFilters


@dataclass(frozen=True)
class GetEnquiryActCountQueryHandler(BaseQueryHandler[GetEnquiryActCountQuery, int]):
    """Обработчик подсчета актов"""
    act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetEnquiryActCountQuery) -> int:
        return await self.act_repository.get_count(query.filters)


@dataclass(frozen=True)
class GetEnquiryActByIdQuery(BaseQuery):
    """Запрос акта по ID"""
    act_id: UUID


@dataclass(frozen=True)
class GetEnquiryActByIdQueryHandler(BaseQueryHandler[GetEnquiryActByIdQuery, Optional[EnquiryAct]]):
    """Обработчик получения акта по ID"""
    act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetEnquiryActByIdQuery) -> Optional[EnquiryAct]:
        return await self.act_repository.get_by_id(query.act_id)


@dataclass(frozen=True)
class GetUnlinkedEnquiryActsQuery(BaseQuery):
    """Запрос непривязанных актов"""
    pass


@dataclass(frozen=True)
class GetUnlinkedEnquiryActsQueryHandler(BaseQueryHandler[GetUnlinkedEnquiryActsQuery, list[EnquiryAct]]):
    """Обработчик получения непривязанных актов"""
    act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetUnlinkedEnquiryActsQuery) -> list[EnquiryAct]:
        return await self.act_repository.get_unlinked()


@dataclass(frozen=True)
class GetTagPatternsQuery(BaseQuery):
    """Запрос агрегации паттернов по тегам"""
    tag_field: str = "cause_categories"
    limit: int = 10


@dataclass(frozen=True)
class GetTagPatternsQueryHandler(BaseQueryHandler[GetTagPatternsQuery, list[tuple[str, int]]]):
    """Обработчик агрегации паттернов"""
    act_repository: BaseEnquiryActRepository

    async def handle(self, query: GetTagPatternsQuery) -> list[tuple[str, int]]:
        return await self.act_repository.get_tag_patterns(
            tag_field=query.tag_field,
            limit=query.limit,
        )
