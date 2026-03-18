from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel
from punq import Container

from src.domain.entities.users import UserEntity
from src.application.exceptions.base import ApplicationException
from src.application.exceptions.incidents import IncidentNotFoundException
from src.presentation.api.v1.auth import get_current_user
from src.settings.config import MAX_UPLOAD_SIZE

from src.application.commands.incidents import (
    CreateIncidentCommand,
    ImportSapDataCommand,
    ImportIncidentJournalCommand,
)
from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    Region,
    InvestigationStatus,
    WorkExperience,
    InjuryType,
)
from src.application.queries.incidents import (
    GetIncidentsQuery,
    GetIncidentByIdQuery,
    GetIncidentCountQuery,
    GetEnquiryActsByIncidentQuery,
    GetRecommendationsQuery,
)
from src.application.filters.incidents import IncidentFilters
from src.application.filters.common import PaginationIn
from src.application.mediator.base import Mediator
from src.infrastructure.di.containers import init_container
from src.presentation.api.v1.incidents.schemas import (
    CreateIncidentRequestSchema,
    IncidentResponseSchema,
    PaginatedIncidentsResponseSchema,
    RecommendationResponseSchema,
    IncidentFiltersSchema,
    ImportJournalResponseSchema,
    ImportJournalBatchResponseSchema,
    ImportJournalFileResultSchema,
)
from src.presentation.api.v1.acts.schemas import EnquiryActBriefSchema


router = APIRouter(prefix='/incidents', tags=['incidents'])


# --- JSON-схемы для file_id-based эндпоинтов ---

class ImportJournalRequestSchema(BaseModel):
    """Импорт одного журнала по file_id."""
    file_id: UUID


class ImportJournalBatchRequestSchema(BaseModel):
    """Пакетный импорт журналов по file_ids."""
    file_ids: list[UUID]


# --- CRUD ---

@router.post('/', response_model=IncidentResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_incident_handler(
    schema: CreateIncidentRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> IncidentResponseSchema:
    """Создать инцидент"""
    mediator: Mediator = container.resolve(Mediator)

    command = CreateIncidentCommand(
        incident_date=schema.incident_date,
        company=Company(schema.company),
        classification=IncidentClassification(schema.classification),
        region=Region(schema.region),
        location=schema.location,
        description=schema.description,
        investigation_status=InvestigationStatus.NOT_COMPLETED,
        incident_time=schema.incident_time,
        dzo=schema.dzo,
        victim_name=schema.victim_name,
        victim_birth_date=schema.victim_birth_date,
        victim_position=schema.victim_position,
        victim_work_experience=WorkExperience(schema.victim_work_experience) if schema.victim_work_experience else None,
        injury_type=InjuryType(schema.injury_type) if schema.injury_type else None,
        diagnosis=schema.diagnosis,
        work_type=schema.work_type,
        equipment=schema.equipment,
        safety_responsible_person=schema.safety_responsible_person,
        weather_conditions=schema.weather_conditions,
        victim_count=schema.victim_count,
        fatality_count=schema.fatality_count,
        safety_training_completed=schema.safety_training_completed,
        is_recurrent=schema.is_recurrent,
        regulatory_compliant=schema.regulatory_compliant,
    )
    incident, *_ = await mediator.handle_command(command)
    return IncidentResponseSchema.from_entity(incident)


@router.get('/', response_model=PaginatedIncidentsResponseSchema)
async def get_incidents_handler(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
    filters: IncidentFiltersSchema = Depends(),
) -> PaginatedIncidentsResponseSchema:
    """Получить список инцидентов с фильтрацией и пагинацией"""
    mediator: Mediator = container.resolve(Mediator)

    incident_filters = IncidentFilters(**filters.model_dump())
    pagination = PaginationIn(limit=limit, offset=offset)

    query = GetIncidentsQuery(filters=incident_filters, pagination=pagination)
    count_query = GetIncidentCountQuery(filters=incident_filters)

    incidents = await mediator.handle_query(query)
    total = await mediator.handle_query(count_query)

    items = [IncidentResponseSchema.from_entity(incident) for incident in incidents]

    return PaginatedIncidentsResponseSchema(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get('/{incident_id}', response_model=IncidentResponseSchema)
async def get_incident_handler(
    incident_id: UUID,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> IncidentResponseSchema:
    """Получить детали инцидента"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetIncidentByIdQuery(incident_id=incident_id)
    incident = await mediator.handle_query(query)

    if not incident:
        raise IncidentNotFoundException(incident_id=incident_id)

    return IncidentResponseSchema.from_entity(incident)


# --- Импорт журналов ---

@router.post('/import/journal', response_model=ImportJournalResponseSchema)
async def import_journal_handler(
    body: ImportJournalRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> ImportJournalResponseSchema:
    """Импорт журнала инцидентов по file_id (файл уже в S3)."""
    mediator: Mediator = container.resolve(Mediator)

    command = ImportIncidentJournalCommand(file_id=body.file_id)
    results = await mediator.handle_command(command)

    return ImportJournalResponseSchema(**results[0])


@router.post('/import/journal/batch', response_model=ImportJournalBatchResponseSchema)
async def import_journal_batch_handler(
    body: ImportJournalBatchRequestSchema,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> ImportJournalBatchResponseSchema:
    """Пакетный импорт журналов. Файлы уже в S3."""
    mediator: Mediator = container.resolve(Mediator)

    file_results: list[ImportJournalFileResultSchema] = []
    total_processed = 0
    total_created = 0
    total_updated = 0
    successful_files = 0

    for file_id in body.file_ids:
        try:
            command = ImportIncidentJournalCommand(file_id=file_id)
            results = await mediator.handle_command(command)
            result_dict = results[0]

            file_results.append(ImportJournalFileResultSchema(
                file_id=file_id,
                processed=result_dict['processed'],
                created=result_dict['created'],
                updated=result_dict['updated'],
                adopted_acts=result_dict.get('adopted_acts', 0),
                warning=result_dict.get('warning'),
            ))
            total_processed += result_dict['processed']
            total_created += result_dict['created']
            total_updated += result_dict['updated']
            successful_files += 1
        except (ApplicationException, OSError, ValueError) as e:
            file_results.append(ImportJournalFileResultSchema(
                file_id=file_id,
                processed=0,
                created=0,
                updated=0,
                error=str(e) or repr(e),
            ))

    return ImportJournalBatchResponseSchema(
        total_files=len(body.file_ids),
        successful_files=successful_files,
        failed_files=len(body.file_ids) - successful_files,
        total_processed=total_processed,
        total_created=total_created,
        total_updated=total_updated,
        files=file_results,
    )


# --- SAP (STUB — отложен) ---

@router.post('/import', status_code=status.HTTP_202_ACCEPTED)
async def import_sap_data_handler(
    file: UploadFile = File(...),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> dict:
    """Импорт данных из SAP Excel (STUB)"""
    mediator: Mediator = container.resolve(Mediator)

    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail='Файл превышает допустимый размер')

    command = ImportSapDataCommand(
        file_content=file_content,
        filename=file.filename or "unknown.xlsx",
    )

    result, *_ = await mediator.handle_command(command)

    return {
        'status': 'processing',
        'message': 'Импорт SAP завершён',
        'processed': result.get('processed', 0),
        'created': result.get('created', 0),
        'updated': result.get('updated', 0),
    }


# --- Акты по инциденту (GET — оставлен для удобства фронта) ---

@router.get('/{incident_id}/acts', response_model=list[EnquiryActBriefSchema])
async def get_investigation_acts_handler(
    incident_id: UUID,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> list[EnquiryActBriefSchema]:
    """Получить акты расследования по инциденту"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetEnquiryActsByIncidentQuery(incident_id=incident_id)
    acts = await mediator.handle_query(query)

    return [EnquiryActBriefSchema.from_entity(act) for act in acts]


# --- Рекомендации ---

@router.get('/{incident_id}/recommendations', response_model=list[RecommendationResponseSchema])
async def get_recommendations_handler(
    incident_id: UUID,
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> list[RecommendationResponseSchema]:
    """Получить рекомендации по инциденту"""
    mediator: Mediator = container.resolve(Mediator)

    query = GetRecommendationsQuery(incident_id=incident_id)
    recommendations = await mediator.handle_query(query)

    return [
        RecommendationResponseSchema(
            id=rec.id,
            recommendation_text=rec.recommendation_text,
            priority=rec.priority.value,
            status=rec.status.value,
            legal_references=rec.legal_references,
            created_at=rec.created_at,
        )
        for rec in recommendations
    ]
