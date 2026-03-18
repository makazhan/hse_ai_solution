from dataclasses import dataclass

from src.application.exceptions.base import ApplicationException


@dataclass(frozen=True, eq=False)
class LLMExtractionFailedException(ApplicationException):
    detail: str = ""

    @property
    def message(self):
        return f"Ошибка LLM-извлечения: {self.detail}"


@dataclass(frozen=True, eq=False)
class LLMReportGenerationFailedException(ApplicationException):
    detail: str = ""

    @property
    def message(self):
        return f"Ошибка генерации отчёта: {self.detail}"
