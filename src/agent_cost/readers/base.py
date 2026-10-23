"""Reader plugin interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..models import Record


@dataclass(frozen=True)
class Context:
    """Where a JSON line came from."""

    project: str
    file_stem: str


class Reader(Protocol):
    """A reader turns one decoded JSON line into a Record, or None to skip it."""

    name: str

    def parse(self, obj: dict[str, Any], ctx: Context) -> Record | None: ...
