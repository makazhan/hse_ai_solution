from dataclasses import (
    dataclass,
    field,
)
from typing import Optional

from src.domain.entities.base import BaseEntity


@dataclass
class GroupEntity(BaseEntity):
    name: str
    path: str
    children: list['GroupEntity'] = field(default_factory=list)


@dataclass
class UserEntity(BaseEntity):
    username: str
    email: str
    full_name: str
    email_verified: bool
    enabled: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list[str] = field(default_factory=list)
    groups: list[GroupEntity] = field(default_factory=list)
