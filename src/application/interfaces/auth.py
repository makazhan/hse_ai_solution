from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.users import UserEntity


@dataclass
class BaseAuthClient(ABC):
    @abstractmethod
    async def validate_session(self, session_id: str) -> UserEntity:
        ...
