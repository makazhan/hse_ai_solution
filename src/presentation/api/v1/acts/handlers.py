import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from punq import Container

from src.application.commands.incidents import UploadEnquiryActCommand
from src.application.exceptions.base import ApplicationException
from src.application.exceptions.incidents import EnquiryActNotFoundException
from src.domain.entities.users import UserEntity
from src.presentation.api.v1.auth import get_current_user
from src.application.queries.enquiry_acts import (
    GetEnquiryActsQuery,
    GetEnquiryActCountQuery,
    GetEnquiryActByIdQuery,
    GetUnlinkedEnquiryActsQuery,
    GetTagPatternsQuery,
)
from src.application.filters.enquiry_acts import EnquiryActFilters
from src.application.filters.common import PaginationIn
from src.application.mediator.base import Mediator
from src.infrastructure.di.containers import init_container
from src.presentation.api.v1.acts.schemas import (
    EnquiryActFiltersSchema,
    EnquiryActResponseSchema,
    EnquiryActBriefSchema,
    PaginatedEnquiryActsResponseSchema,
    TagPatternSchema,
    TagPatternsResponseSchema,
    UploadActFileResultSchema,
    UploadActsBatchResponseSchema,
)


router = APIRouter(prefix='/acts', tags=['acts'])


@router.get('/', response_model=PaginatedEnquiryActsResponseSchema)
async def get_acts_handler(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
    filters: EnquiryActFiltersSchema = Depends(),
) -> PaginatedEnquiryActsResponseSchema:
    """Получить список актов расследования с фильтрацией и пагинацией"""
    mediator: Mediator = container.resolve(Mediator)

    act_filters = EnquiryActFilters(**filters.model_dump())
    pagination = PaginationIn(limit=limit, offset=offset)

    query = GetEnquiryActsQuery(filters=act_filters, pagination=pagination)
    count_query = GetEnquiryActCountQuery(filters=act_filters)

    acts = await mediator.handle_query(query)
    total = await mediator.handle_query(count_query)

    items = [EnquiryActBriefSchema.from_entity(act) for act in acts]

    return PaginatedEnquiryActsResponseSchema(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get('/unlinked', response_model=list[EnquiryActBriefSchema])
async def get_unlinked_acts_handler(
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> list[EnquiryActBriefSchema]:
    """Получить непривязанные акты (очередь на обработку)"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetUnlinkedEnquiryActsQuery()
    acts = await mediator.handle_query(query)

    return [EnquiryActBriefSchema.from_entity(act) for act in acts]


@router.get('/patterns', response_model=TagPatternsResponseSchema)
async def get_patterns_handler(
    limit: int = Query(10, ge=1, le=100),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> TagPatternsResponseSchema:
    """Агрегация паттернов: топ-N категорий причин, нарушений, отраслей"""
    mediator: Mediator = container.resolve(Mediator)

    cause_query = GetTagPatternsQuery(tag_field="cause_categories", limit=limit)
    violation_query = GetTagPatternsQuery(tag_field="violation_types", limit=limit)
    industry_query = GetTagPatternsQuery(tag_field="industry_tags", limit=limit)

    causes, violations, industries = await asyncio.gather(
        mediator.handle_query(cause_query),
        mediator.handle_query(violation_query),
        mediator.handle_query(industry_query),
    )

    return TagPatternsResponseSchema(
        cause_categories=[TagPatternSchema(tag=t, count=c) for t, c in causes],
        violation_types=[TagPatternSchema(tag=t, count=c) for t, c in violations],
        industry_tags=[TagPatternSchema(tag=t, count=c) for t, c in industries],
    )


@router.get('/search', response_model=PaginatedEnquiryActsResponseSchema)
async def search_acts_handler(
    cause_category: Optional[str] = Query(None),
    violation_type: Optional[str] = Query(None),
    industry_tag: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> PaginatedEnquiryActsResponseSchema:
    """Поиск актов по тегам"""
    mediator: Mediator = container.resolve(Mediator)

    act_filters = EnquiryActFilters(
        cause_category=cause_category,
        violation_type=violation_type,
        industry_tag=industry_tag,
    )
    pagination = PaginationIn(limit=limit, offset=offset)

    query = GetEnquiryActsQuery(filters=act_filters, pagination=pagination)
    count_query = GetEnquiryActCountQuery(filters=act_filters)

    acts = await mediator.handle_query(query)
    total = await mediator.handle_query(count_query)

    items = [EnquiryActBriefSchema.from_entity(act) for act in acts]

    return PaginatedEnquiryActsResponseSchema(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# --- JSON-схемы для upload ---

class UploadActRequestSchema(BaseModel):
    """Загрузка одного акта по file_id."""
    file_id: UUID
    incident_id: Optional[UUID] = None


class UploadActsBatchRequestSchema(BaseModel):
    """Пакетная загрузка актов по file_ids."""
    file_ids: list[UUID]
    incident_id: Optional[UUID] = None


# --- Upload эндпоинты ---

@router.post('/upload', response_model=EnquiryActResponseSchema,
             status_code=status.HTTP_201_CREATED)
async def upload_act_handler(
    body: UploadActRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> EnquiryActResponseSchema:
    """Загрузить акт расследования (PDF/DOCX). Файл уже в S3."""
    mediator: Mediator = container.resolve(Mediator)

    command = UploadEnquiryActCommand(
        file_id=body.file_id,
        incident_id=body.incident_id,
    )
    act, *_ = await mediator.handle_command(command)

    return EnquiryActResponseSchema.from_entity(act)


@router.post('/upload/batch', response_model=UploadActsBatchResponseSchema,
             status_code=status.HTTP_201_CREATED)
async def upload_acts_batch_handler(
    body: UploadActsBatchRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> UploadActsBatchResponseSchema:
    """Пакетная загрузка актов. Файлы уже в S3. Частичные ошибки не прерывают пакет."""
    mediator: Mediator = container.resolve(Mediator)
    results: list[UploadActFileResultSchema] = []
    successful = 0

    for file_id in body.file_ids:
        try:
            command = UploadEnquiryActCommand(
                file_id=file_id,
                incident_id=body.incident_id,
            )
            act, *_ = await mediator.handle_command(command)
            results.append(UploadActFileResultSchema(
                file_id=file_id,
                act=EnquiryActBriefSchema.from_entity(act),
            ))
            successful += 1
        except (ApplicationException, OSError, ValueError) as e:
            results.append(UploadActFileResultSchema(
                file_id=file_id,
                error=str(e) or repr(e),
            ))

    return UploadActsBatchResponseSchema(
        total_files=len(body.file_ids),
        successful=successful,
        failed=len(body.file_ids) - successful,
        results=results,
    )


# --- By ID ---

@router.get('/{act_id}', response_model=EnquiryActResponseSchema)
async def get_act_by_id_handler(
    act_id: UUID,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> EnquiryActResponseSchema:
    """Получить полные данные акта расследования"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetEnquiryActByIdQuery(act_id=act_id)
    act = await mediator.handle_query(query)

    if not act:
        raise EnquiryActNotFoundException(act_id=act_id)

    return EnquiryActResponseSchema.from_entity(act)
