from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseResult:
    """Результат парсинга журнала.

    Args:
        rows: список словарей для создания Incident.
        errors: сообщения об ошибках по пропущенным строкам.
    """
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class JournalParser(ABC):
    """Интерфейс парсера журнала инцидентов"""

    @abstractmethod
    def parse(self, file_content: bytes, filename: str) -> ParseResult:
        """Парсинг файла журнала в структурированные данные инцидентов.

        Args:
            file_content: байты загруженного файла.
            filename: имя файла (для определения расширения).

        Returns:
            ParseResult с распарсенными строками и ошибками.

        Raises:
            UnsupportedFileTypeException: расширение файла не поддерживается.
            FileParseException: файл не читается или отсутствуют обязательные колонки.
        """
        ...
