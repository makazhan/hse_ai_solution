import logging
from typing import Optional

from src.settings.config import Config
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

logger = logging.getLogger(__name__)


def build_sa_engine(config: Config) -> AsyncEngine:
    engine = create_async_engine(
        url=config.full_db_url,
        pool_size=20,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    return engine


def build_sa_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return session_factory


def build_refs_engine(config: Config) -> Optional[AsyncEngine]:
    """Движок для БД справочников (НПА/ВНД). Возвращает None если REFS_POSTGRES_HOST не задан."""
    if not config.refs_db_enabled:
        logger.info("REFS DB отключена: REFS_POSTGRES_HOST не задан")
        return None
    engine = create_async_engine(
        url=config.refs_db_url,
        pool_size=20,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    logger.info("REFS DB engine создан: %s:%s/%s",
                config.REFS_POSTGRES_HOST, config.REFS_POSTGRES_PORT, config.REFS_POSTGRES_DB)
    return engine


def build_refs_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
