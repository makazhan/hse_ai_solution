from dataclasses import dataclass

import httpx
from httpx import AsyncClient

from src.application.exceptions.auth import (
    AuthClientBadRequestException,
    AuthServiceUnavailableException,
)
from src.application.interfaces.auth import BaseAuthClient
from src.domain.entities.users import GroupEntity, UserEntity


@dataclass
class HttpxAuthClient(BaseAuthClient):
    http_client: AsyncClient
    base_url: str

    async def validate_session(self, session_id: str) -> UserEntity:
        try:
            response = await self.http_client.get(
                url=f'{self.base_url}/v1/oauth/me',
                cookies={'session_id': session_id},
            )
        except httpx.HTTPError:
            raise AuthServiceUnavailableException()

        if not response.is_success:
            raise AuthClientBadRequestException(session_id)

        user_data = response.json()

        return self._convert_user_data_to_entity(user_data)

    def _convert_group_data_to_entity(self, group_data: dict) -> GroupEntity:
        return GroupEntity(
            id=group_data['id'],
            name=group_data['name'],
            path=group_data['path'],
            children=[
                self._convert_group_data_to_entity(child)
                for child in group_data.get('children', [])
            ],
        )

    def _convert_user_data_to_entity(self, user_data: dict) -> UserEntity:
        return UserEntity(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data['full_name'],
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            email_verified=user_data.get('email_verified', False),
            enabled=user_data.get('enabled', False),
            roles=user_data.get('roles', []),
            groups=[
                self._convert_group_data_to_entity(g)
                for g in user_data.get('groups', [])
            ],
        )
