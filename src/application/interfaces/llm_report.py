"""Интерфейс сервиса генерации аналитического отчёта через LLM."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseLLMReportService(ABC):

    @abstractmethod
    async def generate_report(self, context: dict) -> dict:
        """Сгенерировать аналитический отчёт на основе подготовленного контекста.

        Args:
            context: словарь с ключами summary, incidents_sample,
                     cause_patterns, act_summaries, recurrence_data.

        Returns:
            Словарь с секциями отчёта (валидирован через Pydantic).
        """
        ...

    @abstractmethod
    async def generate_section(self, section_name: str, context: dict) -> dict:
        """Сгенерировать одну секцию аналитического отчёта.

        Args:
            section_name: имя секции (causes / risks / recommendations).
            context: входные данные для секции.

        Returns:
            Словарь с полями секции (валидирован через Pydantic).
        """
        ...
