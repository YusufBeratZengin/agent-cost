"""Filtering and aggregation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from .models import Record
from .pricing import PriceTable

DIMENSIONS = ("day", "session", "project", "model")


def parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid date {text!r}; use YYYY-MM-DD") from exc


def filter_records(
    records: Iterable[Record],
    since: date | None = None,
    until: date | None = None,
    project: str | None = None,
    model: str | None = None,
) -> list[Record]:
    """Keep records inside ``[since, until]`` (UTC days, inclusive).

    With a date filter active, records without a timestamp are dropped.
    """
    lo = datetime.combine(since, time.min, tzinfo=timezone.utc) if since else None
    hi = datetime.combine(until, time.max, tzinfo=timezone.utc) if until else None
    out: list[Record] = []
    for rec in records:
        if (lo or hi) and rec.timestamp is None:
            continue
        if lo and rec.timestamp and rec.timestamp < lo:
            continue
        if hi and rec.timestamp and rec.timestamp > hi:
            continue
        if project and project.lower() not in rec.project.lower():
            continue
        if model and model.lower() not in rec.model.lower():
            continue
        out.append(rec)
    return out


@dataclass
class Row:
    keys: tuple[str, ...]
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost: float = 0.0
    unpriced_requests: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )

    def add(self, rec: Record, cost: float | None) -> None:
        self.requests += 1
        self.input_tokens += rec.input_tokens
        self.output_tokens += rec.output_tokens
        self.cache_read_tokens += rec.cache_read_tokens
        self.cache_write_tokens += rec.cache_write_tokens
        if cost is None:
            self.unpriced_requests += 1
        else:
            self.cost += cost


def _key(rec: Record, dim: str) -> str:
    if dim == "day":
        return rec.day
    return str(getattr(rec, dim))


def build_report(
    records: Iterable[Record],
    prices: PriceTable,
    by: Iterable[str] = ("day",),
) -> tuple[list[Row], Row]:
    """Group records by the given dimensions. Returns (rows, grand total)."""
    dims = tuple(by)
    if not dims:
        raise ValueError("at least one dimension is required")
    for dim in dims:
        if dim not in DIMENSIONS:
            raise ValueError(f"unknown dimension {dim!r}; choose from {', '.join(DIMENSIONS)}")
    groups: dict[tuple[str, ...], Row] = {}
    total = Row(keys=("TOTAL",))
    for rec in records:
        cost = prices.cost(rec)
        key = tuple(_key(rec, d) for d in dims)
        groups.setdefault(key, Row(keys=key)).add(rec, cost)
        total.add(rec, cost)
    rows = list(groups.values())
    if dims[0] == "day":
        rows.sort(key=lambda r: r.keys)
    else:
        rows.sort(key=lambda r: (-r.cost, -r.total_tokens, r.keys))
    return rows, total
