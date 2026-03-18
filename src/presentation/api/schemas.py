from typing import (
    Any,
    Generic,
    TypeVar,
)

from pydantic import (
    BaseModel,
    Field,
)

from src.application.filters.common import PaginationIn

TData = TypeVar("TData")
TMeta = TypeVar("TMeta")


class PingResponseSchema(BaseModel):
    status: str


class ErrorSchema(BaseModel):
    error: str


class PaginationInSchema(BaseModel):
    offset: int = 0
    limit: int = 10

    def to_application(self) -> PaginationIn:
        return PaginationIn(
            offset=self.offset,
            limit=self.limit,
        )


class PaginationOutSchema(PaginationInSchema):
    count: int


class ApiResponse(BaseModel, Generic[TData]):
    data: TData | dict = Field(default_factory=dict)
    meta: TMeta | dict[str, Any] = Field(default_factory=dict)
