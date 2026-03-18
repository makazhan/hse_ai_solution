from abc import ABC
from dataclasses import dataclass

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.application.filters.common import PaginationIn


@dataclass
class BaseSqlAlchemyRepository(ABC):
    _async_sessionmaker: async_sessionmaker

    @staticmethod
    def _paginate_query(query: Select, pagination: PaginationIn):
        return query.limit(pagination.limit).offset(pagination.offset)
