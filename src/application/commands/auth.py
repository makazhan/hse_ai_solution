from dataclasses import dataclass, field

from src.application.commands.base import BaseCommand, CommandHandler
from src.application.interfaces.auth import BaseAuthClient
from src.application.mediator.base import Mediator
from src.domain.entities.users import UserEntity


@dataclass(frozen=True)
class AuthCommand(BaseCommand):
    session_id: str


@dataclass(frozen=True)
class AuthCommandHandler(CommandHandler[AuthCommand, UserEntity]):
    auth_client: BaseAuthClient
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    async def handle(self, command: AuthCommand) -> UserEntity:
        return await self.auth_client.validate_session(command.session_id)
