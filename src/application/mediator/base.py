from collections import defaultdict
from dataclasses import (
    dataclass,
    field,
)
from typing import Iterable

from src.application.commands.base import (
    BaseCommand,
    CommandHandler,
    CR,
    CT,
)
from src.application.events.base import (
    ER,
    ET,
    EventHandler,
)
from src.application.exceptions.mediator import (
    CommandHandlersNotRegisteredException,
    QueryHandlersNotRegisteredException,
)
from src.application.queries.base import (
    BaseQuery,
    BaseQueryHandler,
    QR,
    QT,
)
from src.domain.events.base import BaseEvent


@dataclass(eq=False)
class Mediator:
    events_map: dict[ET, list[EventHandler]] = field(
        default_factory=lambda: defaultdict(list),
        kw_only=True,
    )
    commands_map: dict[CT, list[CommandHandler]] = field(
        default_factory=lambda: defaultdict(list),
        kw_only=True,
    )
    queries_map: dict[QT, BaseQueryHandler] = field(
        default_factory=dict,
        kw_only=True,
    )

    def register_event(self, event: type[ET], event_handlers: Iterable[EventHandler[ET, ER]]) -> None:
        self.events_map[event].extend(event_handlers)

    def register_command(self, command: type[CT], command_handlers: Iterable[CommandHandler[CT, CR]]) -> None:
        self.commands_map[command].extend(command_handlers)

    def register_query(self, query: type[QT], query_handler: BaseQueryHandler[QT, QR]) -> None:
        self.queries_map[query] = query_handler

    async def publish(self, events: Iterable[BaseEvent]) -> Iterable[ER]:
        result = []

        for event in events:
            handlers: Iterable[EventHandler] = self.events_map[event.__class__]
            result.extend([await handler.handle(event) for handler in handlers])

        return result

    async def handle_command(self, command: BaseCommand) -> Iterable[CR]:
        command_type = command.__class__
        handlers = self.commands_map.get(command_type)

        if not handlers:
            raise CommandHandlersNotRegisteredException(command_type=command_type)

        result = [await handler.handle(command=command) for handler in handlers]
        return result

    async def handle_command_single(self, command: BaseCommand) -> CR:
        """Выполнить команду, ожидая ровно одного обработчика.

        Raises:
            CommandHandlersNotRegisteredException: обработчик не зарегистрирован.
            AssertionError: зарегистрировано более одного обработчика.
        """
        command_type = command.__class__
        handlers = self.commands_map.get(command_type)

        if not handlers:
            raise CommandHandlersNotRegisteredException(command_type=command_type)

        assert len(handlers) == 1, (
            f"handle_command_single ожидает 1 обработчик для {command_type.__name__}, "
            f"зарегистрировано {len(handlers)}"
        )

        return await handlers[0].handle(command=command)

    async def handle_query(self, query: BaseQuery) -> QR:
        query_type = query.__class__
        handler = self.queries_map.get(query_type)

        if not handler:
            raise QueryHandlersNotRegisteredException(query_type=query_type)

        return await handler.handle(query=query)
