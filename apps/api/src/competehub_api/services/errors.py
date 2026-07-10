from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServiceError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None
