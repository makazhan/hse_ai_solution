import uuid
from typing import Optional

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import APIKeyHeader
from punq import Container

from src.application.commands.auth import AuthCommand
from src.application.exceptions.auth import AuthServiceUnavailableException
from src.application.exceptions.base import ApplicationException
from src.application.mediator.base import Mediator
from src.domain.entities.users import UserEntity
from src.infrastructure.di.containers import init_container
from src.settings.config import Config

header_scheme = APIKeyHeader(name='X-Session-ID', auto_error=False)


def _mock_user() -> UserEntity:
    """Заглушка для локальной разработки при AUTH_ENABLED=false."""
    return UserEntity(
        id=uuid.UUID('00000000-0000-0000-0000-000000000000'),
        username='dev-user',
        email='dev@localhost',
        full_name='Dev User',
        email_verified=True,
        enabled=True,
    )


async def get_current_user(
        request: Request,
        session_id_header: Optional[str] = Depends(header_scheme),
        container: Container = Depends(init_container),
) -> UserEntity:
    config: Config = container.resolve(Config)

    if not config.AUTH_ENABLED:
        return _mock_user()

    session_id = session_id_header or request.cookies.get('session_id')

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'error': 'Session ID не предоставлен'},
        )

    mediator: Mediator = container.resolve(Mediator)

    try:
        user, *_ = await mediator.handle_command(
            AuthCommand(session_id=session_id),
        )
    except AuthServiceUnavailableException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={'error': e.message},
        )
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'error': e.message},
        )

    return user
