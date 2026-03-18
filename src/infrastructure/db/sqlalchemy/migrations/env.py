import asyncio
import logging
import os
import re
import secrets

from alembic import context

from src.settings.config import Config
from sqlalchemy import (
    engine_from_config,
    pool,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.util import await_only
from sqlalchemy.util.concurrency import in_greenlet

from src.infrastructure.db.sqlalchemy.models.base import BaseModel

config = context.config

VERSIONS_DIR = os.path.join(os.path.dirname(__file__), "versions")


def get_next_revision_number() -> int:
    """Следующий порядковый номер ревизии."""
    if not os.path.exists(VERSIONS_DIR):
        return 1

    pattern = re.compile(r"^(\d+)_")
    max_num = 0

    for filename in os.listdir(VERSIONS_DIR):
        if filename.endswith(".py"):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

    return max_num + 1


def generate_revision_id() -> str:
    """Генерация ID ревизии: порядковый номер + случайная соль."""
    next_num = get_next_revision_number()
    salt = secrets.token_hex(4)
    return f"{next_num:03d}_{salt}"


def process_revision_directives(context, revision, directives):
    """Хук для установки кастомного ID ревизии."""
    if directives:
        script = directives[0]
        if script.rev_id is None or not script.rev_id.startswith(tuple("0123456789")):
            script.rev_id = generate_revision_id()


target_metadata = BaseModel.metadata

logger = logging.getLogger("alembic.runtime.migration")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

if not (full_url := config.get_main_option("sqlalchemy.url")):
    db_config = Config()
    full_url = db_config.full_db_url


def run_migrations_offline() -> None:
    """Оффлайн-миграции (без подключения к БД)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
            url=full_url,
        ),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Онлайн-миграции (с подключением к БД)."""
    if in_greenlet():
        await_only(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
