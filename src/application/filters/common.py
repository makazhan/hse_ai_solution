from dataclasses import dataclass


@dataclass
class PaginationIn:
    limit: int
    offset: int
