import datetime

from sqlalchemy import (
    MetaData,
    sql,
)
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
    registry,
)


mapper_registry = registry(metadata=MetaData())

metadata = MetaData()
BaseModel = declarative_base(metadata=metadata)


class TimedBaseModel(BaseModel):
    """Абстрактная модель, добавляющая created_at и updated_at timestamp поля к
    модели."""

    __abstract__ = True

    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=sql.func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=sql.func.now(),
        onupdate=sql.func.now(),
    )
