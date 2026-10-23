"""Core data model shared by readers and reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Record:
    """One model response with its token usage."""

    timestamp: datetime | None
    session: str
    project: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    dedupe_key: str | None = None

    @property
    def day(self) -> str:
        return self.timestamp.date().isoformat() if self.timestamp else "unknown"


def to_int(value: Any) -> int:
    """Coerce a JSON value to a non-negative int; anything odd becomes 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return 0


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 string or a Unix epoch (seconds or ms) into aware UTC."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 1e11:  # milliseconds
                seconds /= 1000.0
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        if isinstance(value, str) and value:
            text = value.strip()
            if text.endswith(("Z", "z")):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    return None
