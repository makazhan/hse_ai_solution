from dataclasses import dataclass
from uuid import UUID

from src.application.exceptions.base import ApplicationException, NotFoundException


@dataclass(frozen=True, eq=False)
class UnsupportedFileTypeException(ApplicationException):
    extension: str
    supported: tuple[str, ...]

    @property
    def message(self):
        return f"Неподдерживаемый тип файла: '{self.extension}'. Допустимые: {', '.join(self.supported)}"


@dataclass(frozen=True, eq=False)
class FileParseException(ApplicationException):
    detail: str

    @property
    def message(self):
        return f"Ошибка разбора файла: {self.detail}"


@dataclass(frozen=True, eq=False)
class UploadedFileNotFoundException(NotFoundException):
    file_id: UUID

    @property
    def message(self):
        return f"Загруженный файл {self.file_id} не найден"


@dataclass(frozen=True, eq=False)
class FileTooLargeException(ApplicationException):
    size_bytes: int
    max_bytes: int

    @property
    def message(self):
        return f"Файл слишком большой ({self.size_bytes} байт). Максимум: {self.max_bytes} байт"
