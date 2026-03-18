import asyncio
import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID
import uuid

from src.application.commands.base import BaseCommand, CommandHandler
from src.application.mediator.base import Mediator
from src.application.interfaces.repositories.files import BaseUploadedFileRepository
from src.application.interfaces.repositories.incidents import (
    BaseIncidentRepository,
    BaseEnquiryActRepository,
)
from src.application.interfaces.storage import BaseFileStorage
from src.application.interfaces.ocr import BaseOcrService
from src.application.interfaces.llm_extraction import BaseLLMExtractionService
from src.application.services.act_matching import ActMatchingService
from src.application.exceptions.incidents import IncidentNotFoundException
from src.application.exceptions.files import (
    UnsupportedFileTypeException,
    UploadedFileNotFoundException,
)
from src.application.exceptions.acts import ActMissingCompanyException
from src.application.interfaces.parsers import JournalParser
from src.domain.entities.incidents import Incident, EnquiryAct
from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    Region,
    InjuryType,
    InvestigationStatus,
    WorkExperience,
    DeletionStatus,
    InvestigationResult,
    EnquiryActLinkStatus,
)

logger = logging.getLogger(__name__)

# Маппинг region_from_act → нормализованное значение
_REGION_MAP: dict[str, str] = {
    "Маңғыстау облысы": "Мангистауская область",
    "Өзен кенорны": "Мангистауская область",
    "Ақтас кенорны": "Мангистауская область",
    "город Алматы": "Алматы",
}

# Маппинг подстрока company_name → регион
_COMPANY_REGION_MAP: dict[str, str] = {
    "Oil Services Company": "Мангистауская область",
    "Уранэнерго": "Туркестанская область",
}


def _normalize_region(region: str | None, company_name: str) -> str | None:
    """Нормализация региона: казахские названия → русские, фоллбэк по компании."""
    if region and region in _REGION_MAP:
        return _REGION_MAP[region]
    # Фоллбэк по company_name
    for substr, mapped_region in _COMPANY_REGION_MAP.items():
        if substr in company_name:
            return mapped_region
    return region


# STUB: заглушка для импорта SAP
@dataclass(frozen=True)
class ImportSapDataCommand(BaseCommand):
    """Команда импорта данных из SAP Excel"""
    file_content: bytes
    filename: str

@dataclass(frozen=True)
class ImportSapDataCommandHandler(CommandHandler[ImportSapDataCommand, list[Incident]]):
    """Обработчик импорта SAP данных (STUB)"""
    incident_repository: BaseIncidentRepository
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    async def handle(self, command: ImportSapDataCommand) -> dict:
        """Импорт SAP Excel — перенаправляет на импорт журнала (тот же формат)."""
        journal_command = ImportIncidentJournalCommand(
            file_content=command.file_content,
            filename=command.filename
        )
        return await self._mediator.handle_command_single(journal_command)


@dataclass(frozen=True)
class UploadEnquiryActCommand(BaseCommand):
    """Команда загрузки акта расследования. Файл уже в S3."""
    file_id: UUID
    incident_id: Optional[UUID] = None


@dataclass(frozen=True)
class UploadEnquiryActCommandHandler(CommandHandler[UploadEnquiryActCommand, EnquiryAct]):
    """Скачивает файл из S3, извлекает текст, создаёт EnquiryAct.

    При наличии LLM-сервиса — извлекает структурированные поля.
    При отсутствии явного incident_id — пытается автоматически привязать к инциденту.
    """
    incident_repository: BaseIncidentRepository
    enquiry_act_repository: BaseEnquiryActRepository
    file_repository: BaseUploadedFileRepository
    file_storage: BaseFileStorage
    ocr_service: BaseOcrService | None = None
    llm_extraction_service: BaseLLMExtractionService | None = None
    act_matching_service: ActMatchingService | None = None
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    async def handle(self, command: UploadEnquiryActCommand) -> EnquiryAct:
        # Шаг 1: проверяем существование файла
        uploaded_file = await self.file_repository.get_by_id(command.file_id)
        if not uploaded_file:
            raise UploadedFileNotFoundException(file_id=command.file_id)

        # Проверяем существование инцидента (если указан)
        if command.incident_id:
            incident = await self.incident_repository.get_by_id(command.incident_id)
            if not incident:
                raise IncidentNotFoundException(incident_id=command.incident_id)

        # Шаг 2: скачиваем файл из S3
        file_content = await self.file_storage.download(uploaded_file.s3_key)

        # Шаг 3: извлечение текста (CPU-bound — выносим в поток)
        file_ext = uploaded_file.original_filename.lower().rsplit('.', 1)[-1]

        if file_ext == 'pdf':
            def _parse_pdf(data: bytes) -> str:
                import pymupdf
                doc = pymupdf.open(stream=data, filetype='pdf')
                text = "\n".join([page.get_text() for page in doc])
                doc.close()
                return text
            extracted_text = await asyncio.to_thread(_parse_pdf, file_content)
            # Текстовый слой пуст (скан) — запускаем OCR, если сервис доступен
            if not extracted_text.strip() and self.ocr_service:
                extracted_text = await self.ocr_service.extract_text_from_pdf(file_content)
        elif file_ext == 'docx':
            def _parse_docx(data: bytes) -> str:
                from docx import Document
                from io import BytesIO
                doc = Document(BytesIO(data))
                return "\n".join([para.text for para in doc.paragraphs])
            extracted_text = await asyncio.to_thread(_parse_docx, file_content)
        else:
            raise UnsupportedFileTypeException(extension=file_ext, supported=('pdf', 'docx'))

        # Шаг 4: LLM extraction (graceful degradation)
        extracted_fields: dict = {}
        if extracted_text.strip() and self.llm_extraction_service:
            try:
                extracted_fields = await self.llm_extraction_service.extract_structured_data(
                    extracted_text,
                )
                logger.info(
                    "LLM extraction: извлечено %d полей (file_id=%s)",
                    len(extracted_fields), command.file_id,
                )
            except Exception as exc:
                logger.warning(
                    "LLM extraction не удался (file_id=%s): %s", command.file_id, exc,
                )

        # Шаг 4.1: валидация company_name — без него акт бесполезен
        company = (
            extracted_fields.get('company_name_from_act')
            or extracted_fields.get('company_name')
            or ''
        ).strip()
        if not company:
            logger.warning(
                "Акт без company_name — пропускаем (file_id=%s, filename=%s)",
                command.file_id, uploaded_file.original_filename,
            )
            raise ActMissingCompanyException(file_id=command.file_id)

        # Шаг 4.2: нормализация region_from_act
        extracted_fields['region_from_act'] = _normalize_region(
            extracted_fields.get('region_from_act'),
            company,
        )

        now = datetime.datetime.utcnow()
        try:
            act = EnquiryAct(
                id=uuid.uuid4(),
                incident_id=command.incident_id,
                file_path=uploaded_file.s3_key,
                file_id=command.file_id,
                original_filename=uploaded_file.original_filename,
                extracted_text=extracted_text,
                analysis_result="",
                uploaded_at=now,
                created_at=now,
                updated_at=now,
                **extracted_fields,
            )
        except Exception as exc:
            logger.warning(
                "Ошибка при создании EnquiryAct с LLM-полями (file_id=%s): %s",
                command.file_id, exc,
            )
            act = EnquiryAct(
                id=uuid.uuid4(),
                incident_id=command.incident_id,
                file_path=uploaded_file.s3_key,
                file_id=command.file_id,
                original_filename=uploaded_file.original_filename,
                extracted_text=extracted_text,
                analysis_result="",
                uploaded_at=now,
                created_at=now,
                updated_at=now,
            )

        # Шаг 5: авто-матчинг (если incident_id не указан явно)
        if not command.incident_id and self.act_matching_service:
            try:
                match_result = await self.act_matching_service.find_best_incident_for_act(act)
                if match_result:
                    act.incident_id = match_result.incident_id
                    act.link_status = EnquiryActLinkStatus.AUTO_MATCHED
            except Exception as exc:
                logger.warning(
                    "Авто-матчинг не удался (file_id=%s): %s", command.file_id, exc,
                )

        return await self.enquiry_act_repository.create(act)


@dataclass(frozen=True)
class CreateIncidentCommand(BaseCommand):
    """Команда создания инцидента"""
    incident_date: datetime.date
    company: Company
    classification: IncidentClassification
    region: Region
    location: str
    description: str
    investigation_status: InvestigationStatus

    incident_time: Optional[datetime.time] = None
    dzo: Optional[str] = None
    victim_name: Optional[str] = None
    victim_birth_date: Optional[datetime.date] = None
    victim_position: Optional[str] = None
    victim_work_experience: Optional[WorkExperience] = None
    injury_type: Optional[InjuryType] = None
    diagnosis: Optional[str] = None
    initial_actions: Optional[str] = None
    consequences_elimination_date: Optional[datetime.date] = None
    consequences_elimination_time: Optional[datetime.time] = None
    impact_on_production: Optional[str] = None
    notified_authorities: Optional[str] = None
    preliminary_causes: Optional[str] = None
    consequences_description: Optional[str] = None
    damage_amount_kzt: Optional[float] = None
    investigation_results: Optional[InvestigationResult] = None
    main_causes_from_report: Optional[str] = None
    corrective_actions: Optional[str] = None
    corrective_actions_execution_report: Optional[str] = None
    root_causes: Optional[str] = None
    notes: Optional[str] = None
    deletion_status: Optional[DeletionStatus] = None

    # Фаза A: текстовые
    work_type: Optional[str] = None
    equipment: Optional[str] = None
    safety_responsible_person: Optional[str] = None
    weather_conditions: Optional[str] = None

    # Фаза B: счётчики
    victim_count: int = 1
    fatality_count: int = 0

    # Фаза C: булевые AI-зависимые
    safety_training_completed: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    regulatory_compliant: Optional[bool] = None


@dataclass(frozen=True)
class ImportIncidentJournalCommand(BaseCommand):
    """Команда импорта журнала инцидентов.

    Принимает file_id (файл уже в S3) ИЛИ file_content + filename
    (обратная совместимость для SAP STUB).
    """
    file_id: Optional[UUID] = None
    file_content: Optional[bytes] = None
    filename: Optional[str] = None

@dataclass(frozen=True)
class ImportIncidentJournalCommandHandler(CommandHandler[ImportIncidentJournalCommand, dict]):
    """Обработчик импорта журнала инцидентов"""
    incident_repository: BaseIncidentRepository
    journal_parser: JournalParser
    file_repository: BaseUploadedFileRepository
    file_storage: BaseFileStorage
    act_matching_service: ActMatchingService | None = None
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    async def handle(self, command: ImportIncidentJournalCommand) -> dict:
        """Импорт Excel-журнала в таблицу инцидентов.

        Парсинг → дедупликация по ключу (дата, компания, классификация,
        регион, ФИО, место) → bulk_upsert в одной транзакции →
        усыновление UNLINKED актов (если есть новые инциденты).
        """
        # Получаем байты: из S3 по file_id или из команды напрямую (SAP STUB)
        if command.file_id:
            uploaded_file = await self.file_repository.get_by_id(command.file_id)
            if not uploaded_file:
                raise UploadedFileNotFoundException(file_id=command.file_id)
            file_content = await self.file_storage.download(uploaded_file.s3_key)
            filename = uploaded_file.original_filename
        elif command.file_content:
            file_content = command.file_content
            filename = command.filename or "journal.xlsx"
        else:
            return {"processed": 0, "created": 0, "updated": 0, "adopted_acts": 0, "warning": "Не указан file_id или file_content"}

        result = self.journal_parser.parse(file_content, filename)
        parsed_data = result.rows
        parse_errors = result.errors

        if not parsed_data:
            return {
                "processed": 0,
                "created": 0,
                "updated": 0,
                "adopted_acts": 0,
                "warning": "; ".join(parse_errors[:5]) if parse_errors else None,
            }

        # Диапазон лет из распарсенных дат
        years = {d['incident_date'].year for d in parsed_data if d.get('incident_date')}
        if not years:
            return {
                "processed": len(parsed_data),
                "created": 0,
                "updated": 0,
                "adopted_acts": 0,
                "warning": "Даты не найдены",
            }

        existing_incidents = await self.incident_repository.get_by_year_range(min(years), max(years))

        # Составной ключ дедупликации
        def get_key(inc_data):
            """Ключ: (дата, компания, классификация, регион, ФИО, место).
            Строки нормализуются в нижний регистр со схлопыванием пробелов.
            """
            if isinstance(inc_data, dict):
                date_val = inc_data.get('incident_date')
                company = inc_data.get('company')
                classification = inc_data.get('classification')
                region = inc_data.get('region')
                name = inc_data.get('victim_name')
                loc = inc_data.get('location')
            else:
                date_val = inc_data.incident_date
                company = inc_data.company
                classification = inc_data.classification
                region = inc_data.region
                name = inc_data.victim_name
                loc = inc_data.location

            # Нормализация
            name = " ".join((name or "").split()).lower()
            loc_norm = " ".join((loc or "").split()).lower()

            # date, не datetime
            if isinstance(date_val, datetime.datetime):
                date_val = date_val.date()

            return (date_val, company, classification, region, name, loc_norm)

        existing_map = {get_key(inc): inc for inc in existing_incidents}

        to_create = []
        to_update = []
        now = datetime.datetime.utcnow()

        for data in parsed_data:
            key = get_key(data)
            existing = existing_map.get(key)

            if existing:
                updated_incident = Incident(
                    id=existing.id,
                    created_at=existing.created_at,
                    updated_at=now,
                    **data
                )
                to_update.append(updated_incident)
            else:
                new_incident = Incident(
                    id=uuid.uuid4(),
                    created_at=now,
                    updated_at=now,
                    **data
                )
                to_create.append(new_incident)

        created_count, updated_count = await self.incident_repository.bulk_upsert(to_create, to_update)

        # Усыновление UNLINKED актов (только для новых инцидентов)
        adopted_count = 0
        if to_create and self.act_matching_service:
            try:
                adoptions = await self.act_matching_service.adopt_unlinked_acts(to_create)
                adopted_count = len(adoptions)
            except Exception as exc:
                logger.warning("Ошибка усыновления актов: %s", exc)

        warning = None
        if parse_errors:
            warning = f"{len(parse_errors)} строк(а) пропущено. Первые ошибки: " + "; ".join(parse_errors[:5])

        return {
            "processed": len(parsed_data),
            "created": created_count,
            "updated": updated_count,
            "adopted_acts": adopted_count,
            "warning": warning,
        }


@dataclass(frozen=True)
class CreateIncidentCommandHandler(CommandHandler[CreateIncidentCommand, Incident]):
    """Обработчик создания инцидента"""
    incident_repository: BaseIncidentRepository
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    async def handle(self, command: CreateIncidentCommand) -> Incident:
        """Создание инцидента"""

        incident = Incident(
            **vars(command)
        )

        created_incident = await self.incident_repository.create(incident)
        return created_incident
