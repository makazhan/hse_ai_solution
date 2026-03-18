from dataclasses import dataclass
from uuid import UUID

from src.application.exceptions.base import ApplicationException


@dataclass(frozen=True, eq=False)
class ActMissingCompanyException(ApplicationException):
    file_id: UUID

    @property
    def message(self):
        return (
            f'Акт (file_id={self.file_id}) не содержит названия компании — '
            f'невозможно обработать'
        )
