from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

# Лимит загрузки — 50 МБ
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


class Config(BaseSettings):
    FRONT_URL: str = Field(alias='FRONT_URL', default='http://localhost:8001')
    ROOT_PATH: str = Field(alias='ROOT_PATH', default='/api/dev-tb-expert')
    AGENT_NAME: str = Field(alias='AGENT_NAME')
    NETWORK_ENV: str = Field(alias='NETWORK_ENV', default='test')

    # LLM
    OPENAI_API_KEY: str = Field(alias='OPENAI_API_KEY')
    OPENAI_MODEL: str = Field(alias='OPENAI_MODEL')
    OPENAI_BASE_URL: str = Field(alias='OPENAI_BASE_URL')

    # Embeddings (через LiteLLM, OpenAI-совместимый API)
    EMBEDDING_URL: str = Field(alias='EMBEDDING_URL')
    EMBEDDING_MODEL: str = Field(alias='EMBEDDING_MODEL')

    # OCR Vision (модель на том же LiteLLM-сервере)
    OCR_MODEL: str = Field(alias='OCR_MODEL', default='Qwen/Qwen3-VL-32B-Instruct')

    # LLM Extraction (структурированное извлечение из актов)
    LLM_EXTRACTION_TIMEOUT: float = Field(alias='LLM_EXTRACTION_TIMEOUT', default=120.0)
    LLM_EXTRACTION_CONNECT_TIMEOUT: float = Field(alias='LLM_EXTRACTION_CONNECT_TIMEOUT', default=10.0)
    LLM_EXTRACTION_MAX_RETRIES: int = Field(alias='LLM_EXTRACTION_MAX_RETRIES', default=3)
    LLM_EXTRACTION_MAX_TOKENS: int = Field(alias='LLM_EXTRACTION_MAX_TOKENS', default=16384)

    # LLM Report (аналитический отчёт)
    LLM_REPORT_TIMEOUT: float = Field(alias='LLM_REPORT_TIMEOUT', default=60.0)
    LLM_REPORT_CONNECT_TIMEOUT: float = Field(alias='LLM_REPORT_CONNECT_TIMEOUT', default=10.0)
    LLM_REPORT_MAX_RETRIES: int = Field(alias='LLM_REPORT_MAX_RETRIES', default=3)
    LLM_REPORT_MAX_TOKENS: int = Field(alias='LLM_REPORT_MAX_TOKENS', default=8192)

    # NPA RAG (поиск по НПА для отчёта)
    RAG_NPA_ENABLED: bool = Field(alias='RAG_NPA_ENABLED', default=True)
    NPA_TARGET_IDS_TABLE: str = Field(alias='NPA_TARGET_IDS_TABLE', default='safety_tb_npa')
    NPA_SIMILARITY_THRESHOLD: float = Field(alias='NPA_SIMILARITY_THRESHOLD', default=0.4)
    NPA_VECTOR_TOP_K: int = Field(alias='NPA_VECTOR_TOP_K', default=5)
    NPA_BM25_TOP_K: int = Field(alias='NPA_BM25_TOP_K', default=3)
    NPA_MAX_RESULTS: int = Field(alias='NPA_MAX_RESULTS', default=20)

    # VND (внутренние нормативные документы)
    VND_TABLE_NAME: str = Field(alias='VND_TABLE_NAME', default='safety_tb_vnd')

    # OCR-параметры
    OCR_DPI: int = Field(alias='OCR_DPI', default=150)
    OCR_MAX_IMAGE_KB: int = Field(alias='OCR_MAX_IMAGE_KB', default=500)
    OCR_CONCURRENCY: int = Field(alias='OCR_CONCURRENCY', default=4)
    OCR_MAX_RETRIES: int = Field(alias='OCR_MAX_RETRIES', default=3)
    OCR_TIMEOUT: float = Field(alias='OCR_TIMEOUT', default=300.0)
    OCR_CONNECT_TIMEOUT: float = Field(alias='OCR_CONNECT_TIMEOUT', default=10.0)
    OCR_MAX_TOKENS: int = Field(alias='OCR_MAX_TOKENS', default=16384)

    # AUTH
    AUTH_SERVICE_URL: str = Field(alias="AUTH_SERVICE_URL")
    AUTH_ENABLED: bool = Field(alias="AUTH_ENABLED", default=True)

    # S3 / MinIO (принимает как S3_*, так и MINIO_* env vars)
    S3_ENDPOINT_URL: str = Field(default='http://minio:9000', validation_alias=AliasChoices('S3_ENDPOINT_URL', 'MINIO_ENDPOINT'))
    S3_ACCESS_KEY: str = Field(default='minioadmin', validation_alias=AliasChoices('S3_ACCESS_KEY', 'MINIO_ACCESS_KEY'))
    S3_SECRET_KEY: str = Field(default='minioadmin', validation_alias=AliasChoices('S3_SECRET_KEY', 'MINIO_SECRET_KEY'))
    S3_BUCKET_NAME: str = Field(default='tb-expert-uploads', validation_alias=AliasChoices('S3_BUCKET_NAME', 'MINIO_BUCKET'))
    S3_REGION: str = Field(alias='S3_REGION', default='us-east-1')

    # DB (основная — инциденты, акты, рекомендации, файлы)
    POSTGRES_DB: str = Field(alias='POSTGRES_DB')
    POSTGRES_USER: str = Field(alias='POSTGRES_USER')
    POSTGRES_PASSWORD: str = Field(alias='POSTGRES_PASSWORD')
    POSTGRES_PORT: int = Field(alias='POSTGRES_PORT')
    POSTGRES_HOST: str = Field(alias='POSTGRES_HOST')

    # DB справочников НПА/ВНД (опциональная — all_laws_*, safety_tb_*)
    REFS_POSTGRES_DB: str = Field(alias='REFS_POSTGRES_DB', default='')
    REFS_POSTGRES_USER: str = Field(alias='REFS_POSTGRES_USER', default='')
    REFS_POSTGRES_PASSWORD: str = Field(alias='REFS_POSTGRES_PASSWORD', default='')
    REFS_POSTGRES_PORT: int = Field(alias='REFS_POSTGRES_PORT', default=5432)
    REFS_POSTGRES_HOST: str = Field(alias='REFS_POSTGRES_HOST', default='')

    @property
    def debug(self) -> bool:
        return True if self.NETWORK_ENV.lower() == 'test' else False

    @property
    def full_db_url(self) -> str:
        return "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD,
            self.POSTGRES_HOST,
            self.POSTGRES_PORT,
            self.POSTGRES_DB,
        )

    @property
    def refs_db_enabled(self) -> bool:
        return bool(self.REFS_POSTGRES_HOST)

    @property
    def refs_db_url(self) -> str:
        return "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
            self.REFS_POSTGRES_USER,
            self.REFS_POSTGRES_PASSWORD,
            self.REFS_POSTGRES_HOST,
            self.REFS_POSTGRES_PORT,
            self.REFS_POSTGRES_DB,
        )
