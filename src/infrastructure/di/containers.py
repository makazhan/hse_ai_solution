import logging
from functools import lru_cache

_logger = logging.getLogger(__name__)

from aiojobs import Scheduler
from httpx import AsyncClient
from punq import (
    Container,
    Scope,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.application.commands.auth import (
    AuthCommand,
    AuthCommandHandler,
)
from src.application.commands.files import (
    UploadFileCommand,
    UploadFileCommandHandler,
)
from src.application.commands.incidents import (
    CreateIncidentCommand,
    CreateIncidentCommandHandler,
    ImportIncidentJournalCommand,
    ImportIncidentJournalCommandHandler,
    ImportSapDataCommand,
    ImportSapDataCommandHandler,
    UploadEnquiryActCommand,
    UploadEnquiryActCommandHandler,
)
from src.application.queries.incidents import (
    GetIncidentsQuery,
    GetIncidentsQueryHandler,
    GetIncidentByIdQuery,
    GetIncidentByIdQueryHandler,
    GetIncidentCountQuery,
    GetIncidentCountQueryHandler,
    GetIncidentStatisticsQuery,
    GetIncidentStatisticsQueryHandler,
    GetRegionalHeatmapQuery,
    GetRegionalHeatmapQueryHandler,
    GetAggregatedSummaryQuery,
    GetAggregatedSummaryQueryHandler,
    GetEnquiryActsByIncidentQuery,
    GetEnquiryActsByIncidentQueryHandler,
    GetRecommendationsQuery,
    GetRecommendationsQueryHandler,
)
from src.application.queries.enquiry_acts import (
    GetEnquiryActsQuery,
    GetEnquiryActsQueryHandler,
    GetEnquiryActCountQuery,
    GetEnquiryActCountQueryHandler,
    GetEnquiryActByIdQuery,
    GetEnquiryActByIdQueryHandler,
    GetUnlinkedEnquiryActsQuery,
    GetUnlinkedEnquiryActsQueryHandler,
    GetTagPatternsQuery,
    GetTagPatternsQueryHandler,
)
from src.application.interfaces.auth import BaseAuthClient
from src.application.interfaces.embeddings import BaseEmbeddingService
from src.application.interfaces.llm_extraction import BaseLLMExtractionService
from src.application.interfaces.llm_report import BaseLLMReportService
from src.application.queries.reports import (
    GenerateAnalyticalReportQuery,
    GenerateAnalyticalReportQueryHandler,
)
from src.application.interfaces.ocr import BaseOcrService
from src.application.mediator.base import Mediator
from src.application.services.act_matching import ActMatchingService
from src.application.interfaces.repositories.laws import BaseLawsRepository
from src.application.interfaces.repositories.vnd import BaseVndRepository
from src.application.interfaces.repositories.files import BaseUploadedFileRepository
from src.application.interfaces.repositories.incidents import (
    BaseIncidentRepository,
    BaseEnquiryActRepository,
    BaseRecommendationRepository,
)
from src.application.interfaces.storage import BaseFileStorage
from src.application.interfaces.parsers import JournalParser
from src.application.services.report_npa_search import ReportNpaSearchService
from src.infrastructure.services.journal_parser import PandasJournalParser
from src.infrastructure.db.sqlalchemy.repositories.laws import SqlAlchemyLawsRepository
from src.infrastructure.db.sqlalchemy.repositories.vnd import SqlAlchemyVndRepository
from src.infrastructure.db.sqlalchemy.repositories.files import SqlAlchemyUploadedFileRepository
from src.infrastructure.db.sqlalchemy.repositories.incidents import (
    SqlAlchemyIncidentRepository,
    SqlAlchemyEnquiryActRepository,
    SqlAlchemyRecommendationRepository,
)
from src.infrastructure.integrations.auth import HttpxAuthClient
from src.infrastructure.storage.s3 import S3FileStorage
from src.infrastructure.db.sqlalchemy.main import (
    build_sa_engine, build_sa_session_factory,
    build_refs_engine, build_refs_session_factory,
)
from src.infrastructure.embeddings.openai import BgeEmbeddingService
from src.settings.config import Config


@lru_cache(1)
def init_container():
    return _init_container()


def _init_container() -> Container:
    container = Container()
    container.register(Config, instance=Config(), scope=Scope.singleton)
    config: Config = container.resolve(Config)

    container.register(AsyncEngine, factory=build_sa_engine, config=config, scope=Scope.singleton)
    container.register(
        async_sessionmaker,
        factory=build_sa_session_factory,
        engine=container.resolve(AsyncEngine),
        scope=Scope.singleton,
    )

    # REFS DB — справочники НПА/ВНД (опциональная, отдельный хост)
    refs_engine = build_refs_engine(config)
    refs_session_factory = (
        build_refs_session_factory(refs_engine) if refs_engine else None
    )

    # Laws (НПА) + VND репозитории — используют REFS session factory
    if refs_session_factory:
        def create_laws_repo() -> SqlAlchemyLawsRepository:
            return SqlAlchemyLawsRepository(_async_sessionmaker=refs_session_factory)

        def create_vnd_repo() -> SqlAlchemyVndRepository:
            return SqlAlchemyVndRepository(
                _async_sessionmaker=refs_session_factory,
                table_name=config.VND_TABLE_NAME,
            )

        container.register(BaseLawsRepository, factory=create_laws_repo)
        container.register(BaseVndRepository, factory=create_vnd_repo)
    else:
        _logger.warning("REFS DB не настроена — BaseLawsRepository и BaseVndRepository недоступны")
        container.register(BaseLawsRepository, instance=None)
        container.register(BaseVndRepository, instance=None)

    # Incident repositories
    container.register(
        BaseIncidentRepository,
        SqlAlchemyIncidentRepository,
    )
    container.register(
        BaseEnquiryActRepository,
        SqlAlchemyEnquiryActRepository,
    )
    container.register(
        BaseRecommendationRepository,
        SqlAlchemyRecommendationRepository,
    )

    # File storage (S3 / MinIO)
    container.register(
        BaseUploadedFileRepository,
        SqlAlchemyUploadedFileRepository,
    )

    def create_file_storage() -> BaseFileStorage:
        from aiobotocore.session import AioSession
        return S3FileStorage(_config=config, _session=AioSession())

    container.register(BaseFileStorage, factory=create_file_storage, scope=Scope.singleton)

    def create_embedding_service() -> BaseEmbeddingService:
        from openai import AsyncOpenAI as _AsyncOpenAI
        client = _AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.EMBEDDING_URL,
        )
        return BgeEmbeddingService(
            client=client,
            model=config.EMBEDDING_MODEL,
        )

    container.register(BaseEmbeddingService, factory=create_embedding_service, scope=Scope.singleton)

    # Auth-клиент (внешний сервис сессий)
    def create_auth_client() -> BaseAuthClient:
        return HttpxAuthClient(
            http_client=AsyncClient(timeout=5.0),
            base_url=config.AUTH_SERVICE_URL,
        )

    container.register(BaseAuthClient, factory=create_auth_client, scope=Scope.singleton)

    # OCR-сервис (Vision-модель на LiteLLM) — None если OPENAI_API_KEY не задан

    def create_ocr_service() -> BaseOcrService | None:
        if not config.OPENAI_API_KEY:
            _logger.info("OCR-сервис отключён: OPENAI_API_KEY не задан")
            return None
        from openai import AsyncOpenAI
        from openai import Timeout as OpenAITimeout
        from src.infrastructure.llm.ocr import QwenOcrService, OCR_SYSTEM_PROMPT, OCR_USER_PROMPT
        client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            max_retries=0,  # ретраи в QwenOcrService
            timeout=OpenAITimeout(config.OCR_TIMEOUT, connect=config.OCR_CONNECT_TIMEOUT),
        )
        _logger.info("OCR-сервис активирован (модель: %s)", config.OCR_MODEL)
        return QwenOcrService(
            client=client,
            model=config.OCR_MODEL,
            system_prompt=OCR_SYSTEM_PROMPT,
            user_prompt=OCR_USER_PROMPT,
            dpi=config.OCR_DPI,
            max_image_kb=config.OCR_MAX_IMAGE_KB,
            concurrency=config.OCR_CONCURRENCY,
            max_retries=config.OCR_MAX_RETRIES,
            max_tokens=config.OCR_MAX_TOKENS,
        )

    container.register(BaseOcrService, factory=create_ocr_service, scope=Scope.singleton)

    # LLM Extraction — None если OPENAI_API_KEY не задан
    def create_llm_extraction_service() -> BaseLLMExtractionService | None:
        if not config.OPENAI_API_KEY:
            _logger.info("LLM Extraction отключён: OPENAI_API_KEY не задан")
            return None
        from openai import AsyncOpenAI
        from openai import Timeout as OpenAITimeout
        from src.infrastructure.llm.extraction import LLMExtractionService
        client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            max_retries=0,  # ретраи в LLMExtractionService
            timeout=OpenAITimeout(
                config.LLM_EXTRACTION_TIMEOUT,
                connect=config.LLM_EXTRACTION_CONNECT_TIMEOUT,
            ),
        )
        _logger.info("LLM Extraction активирован (модель: %s)", config.OPENAI_MODEL)
        return LLMExtractionService(
            client=client,
            model=config.OPENAI_MODEL,
            max_retries=config.LLM_EXTRACTION_MAX_RETRIES,
            max_tokens=config.LLM_EXTRACTION_MAX_TOKENS,
        )

    container.register(BaseLLMExtractionService, factory=create_llm_extraction_service, scope=Scope.singleton)

    # LLM Report — аналитический отчёт
    def create_llm_report_service() -> BaseLLMReportService | None:
        if not config.OPENAI_API_KEY:
            _logger.info("LLM Report отключён: OPENAI_API_KEY не задан")
            return None
        from openai import AsyncOpenAI
        from openai import Timeout as OpenAITimeout
        from src.infrastructure.llm.report import LLMReportService
        client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            max_retries=0,  # ретраи в LLMReportService
            timeout=OpenAITimeout(
                config.LLM_REPORT_TIMEOUT,
                connect=config.LLM_REPORT_CONNECT_TIMEOUT,
            ),
        )
        _logger.info("LLM Report активирован (модель: %s)", config.OPENAI_MODEL)
        return LLMReportService(
            client=client,
            model=config.OPENAI_MODEL,
            max_retries=config.LLM_REPORT_MAX_RETRIES,
            max_tokens=config.LLM_REPORT_MAX_TOKENS,
        )

    container.register(BaseLLMReportService, factory=create_llm_report_service, scope=Scope.singleton)

    # Сервис матчинга актов
    def create_act_matching_service() -> ActMatchingService:
        return ActMatchingService(
            incident_repository=container.resolve(BaseIncidentRepository),
            enquiry_act_repository=container.resolve(BaseEnquiryActRepository),
        )

    container.register(ActMatchingService, factory=create_act_matching_service, scope=Scope.singleton)

    container.register(JournalParser, PandasJournalParser)

    # RAG-сервис поиска НПА для отчёта (только если REFS DB доступна и RAG включён)
    def create_report_npa_search() -> ReportNpaSearchService | None:
        if not config.RAG_NPA_ENABLED:
            _logger.info("ReportNpaSearchService отключён: RAG_NPA_ENABLED=false")
            return None
        laws_repo = container.resolve(BaseLawsRepository)
        if laws_repo is None:
            _logger.info("ReportNpaSearchService отключён: REFS DB не настроена")
            return None
        return ReportNpaSearchService(
            embedding_service=container.resolve(BaseEmbeddingService),
            laws_repository=laws_repo,
            _target_table=config.NPA_TARGET_IDS_TABLE,
        )

    container.register(ReportNpaSearchService, factory=create_report_npa_search, scope=Scope.singleton)

    def init_mediator():
        mediator = Mediator()

        # Commands — Auth
        auth_handler = AuthCommandHandler(
            auth_client=container.resolve(BaseAuthClient),
            _mediator=mediator,
        )
        mediator.register_command(
            AuthCommand,
            [auth_handler],
        )

        # Commands — Incidents
        create_incident_handler = CreateIncidentCommandHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
            _mediator=mediator,
        )
        mediator.register_command(
            CreateIncidentCommand,
            [create_incident_handler],
        )

        import_journal_handler = ImportIncidentJournalCommandHandler(
             incident_repository=container.resolve(BaseIncidentRepository),
             journal_parser=container.resolve(JournalParser),
             file_repository=container.resolve(BaseUploadedFileRepository),
             file_storage=container.resolve(BaseFileStorage),
             act_matching_service=container.resolve(ActMatchingService),
             _mediator=mediator,
        )
        mediator.register_command(
            ImportIncidentJournalCommand,
            [import_journal_handler],
        )

        upload_enquiry_act_handler = UploadEnquiryActCommandHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
            enquiry_act_repository=container.resolve(BaseEnquiryActRepository),
            file_repository=container.resolve(BaseUploadedFileRepository),
            file_storage=container.resolve(BaseFileStorage),
            ocr_service=container.resolve(BaseOcrService),
            llm_extraction_service=container.resolve(BaseLLMExtractionService),
            act_matching_service=container.resolve(ActMatchingService),
            _mediator=mediator,
        )
        mediator.register_command(
            UploadEnquiryActCommand,
            [upload_enquiry_act_handler],
        )

        upload_file_handler = UploadFileCommandHandler(
            file_storage=container.resolve(BaseFileStorage),
            file_repository=container.resolve(BaseUploadedFileRepository),
            _mediator=mediator,
        )
        mediator.register_command(
            UploadFileCommand,
            [upload_file_handler],
        )

        import_sap_data_handler = ImportSapDataCommandHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
            _mediator=mediator,
        )
        mediator.register_command(
            ImportSapDataCommand,
            [import_sap_data_handler],
        )

        # Queries — Incidents
        get_incidents_query_handler = GetIncidentsQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )

        mediator.register_query(
            GetIncidentsQuery,
            get_incidents_query_handler,
        )

        get_incident_by_id_query_handler = GetIncidentByIdQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )

        mediator.register_query(
            GetIncidentByIdQuery,
            get_incident_by_id_query_handler,
        )

        # Incident Count Query
        get_incident_count_handler = GetIncidentCountQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )
        mediator.register_query(
            GetIncidentCountQuery,
            get_incident_count_handler,
        )

        # Enquiry Acts by Incident Query
        get_enquiry_acts_by_incident_handler = GetEnquiryActsByIncidentQueryHandler(
            enquiry_act_repository=container.resolve(BaseEnquiryActRepository),
        )
        mediator.register_query(
            GetEnquiryActsByIncidentQuery,
            get_enquiry_acts_by_incident_handler,
        )

        # Recommendations Query
        get_recommendations_handler = GetRecommendationsQueryHandler(
            recommendation_repository=container.resolve(BaseRecommendationRepository),
        )
        mediator.register_query(
            GetRecommendationsQuery,
            get_recommendations_handler,
        )

        # Analytics Queries
        get_statistics_handler = GetIncidentStatisticsQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )
        mediator.register_query(
            GetIncidentStatisticsQuery,
            get_statistics_handler,
        )

        get_heatmap_handler = GetRegionalHeatmapQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )
        mediator.register_query(
            GetRegionalHeatmapQuery,
            get_heatmap_handler,
        )

        get_summary_handler = GetAggregatedSummaryQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
        )
        mediator.register_query(
            GetAggregatedSummaryQuery,
            get_summary_handler,
        )

        # Enquiry Acts Queries
        _act_repo = container.resolve(BaseEnquiryActRepository)

        mediator.register_query(
            GetEnquiryActsQuery,
            GetEnquiryActsQueryHandler(act_repository=_act_repo),
        )
        mediator.register_query(
            GetEnquiryActCountQuery,
            GetEnquiryActCountQueryHandler(act_repository=_act_repo),
        )
        mediator.register_query(
            GetEnquiryActByIdQuery,
            GetEnquiryActByIdQueryHandler(act_repository=_act_repo),
        )
        mediator.register_query(
            GetUnlinkedEnquiryActsQuery,
            GetUnlinkedEnquiryActsQueryHandler(act_repository=_act_repo),
        )
        mediator.register_query(
            GetTagPatternsQuery,
            GetTagPatternsQueryHandler(act_repository=_act_repo),
        )

        # Report Query
        generate_report_handler = GenerateAnalyticalReportQueryHandler(
            incident_repository=container.resolve(BaseIncidentRepository),
            enquiry_act_repository=container.resolve(BaseEnquiryActRepository),
            llm_report_service=container.resolve(BaseLLMReportService),
            npa_search_service=container.resolve(ReportNpaSearchService),
        )
        mediator.register_query(
            GenerateAnalyticalReportQuery,
            generate_report_handler,
        )

        return mediator

    container.register(Mediator, factory=init_mediator)

    container.register(Scheduler, instance=Scheduler(), scope=Scope.singleton)

    return container
