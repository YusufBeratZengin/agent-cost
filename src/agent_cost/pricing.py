"""Price tables: per-million-token prices loaded from TOML or JSON.

The built-in table holds EXAMPLE values only. Prices change and differ per
plan, region and contract, so verify them yourself and pass your own table
with ``--prices``.
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Record

PRICE_KEYS = ("input", "output", "cache_read", "cache_write")


class PriceError(ValueError):
    """Raised when a price file cannot be read or is malformed."""


@dataclass(frozen=True)
class ModelPrice:
    """USD-like units per one million tokens."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0

    def cost(self, record: Record) -> float:
        return (
            record.input_tokens * self.input
            + record.output_tokens * self.output
            + record.cache_read_tokens * self.cache_read
            + record.cache_write_tokens * self.cache_write
        ) / 1_000_000


@dataclass(frozen=True)
class PriceTable:
    models: dict[str, ModelPrice] = field(default_factory=dict)
    currency: str = "USD"
    builtin: bool = False

    def lookup(self, model: str) -> ModelPrice | None:
        """Exact match, else longest key that prefixes the model, else longest substring."""
        name = model.lower()
        if name in self.models:
            return self.models[name]
        for test in (name.startswith, name.__contains__):
            hits = [key for key in self.models if key and test(key)]
            if hits:
                return self.models[max(hits, key=len)]
        return None

    def cost(self, record: Record) -> float | None:
        price = self.lookup(record.model)
        return None if price is None else price.cost(record)


# EXAMPLE VALUES. Not authoritative. Verify against your provider's price page.
_DEFAULT: dict[str, dict[str, float]] = {
    "claude-opus": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-haiku": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25},
    "gpt-4.1": {"input": 2.0, "output": 8.0, "cache_read": 0.5},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6, "cache_read": 0.075},
    "gpt-4o": {"input": 2.5, "output": 10.0, "cache_read": 1.25},
}


def default_prices() -> PriceTable:
    return PriceTable(
        models={name: ModelPrice(**vals) for name, vals in _DEFAULT.items()},
        builtin=True,
    )


def default_prices_toml() -> str:
    lines = [
        "# EXAMPLE VALUES ONLY. Verify prices yourself before trusting any cost figure.",
        "# Unit: currency per 1,000,000 tokens.",
        'currency = "USD"',
        "",
    ]
    for name, vals in _DEFAULT.items():
        lines.append(f'[models."{name}"]')
        for key in PRICE_KEYS:
            if key in vals:
                lines.append(f"{key} = {vals[key]}")
        lines.append("")
    return "\n".join(lines)


def load_prices(path: Path) -> PriceTable:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise PriceError(f"cannot read price file {path}: {exc}") from exc
    try:
        data = json.loads(text) if path.suffix.lower() == ".json" else parse_toml(text)
    except (json.JSONDecodeError, PriceError) as exc:
        raise PriceError(f"invalid price file {path}: {exc}") from exc
    return table_from_dict(data)


def table_from_dict(data: Any) -> PriceTable:
    if not isinstance(data, dict):
        raise PriceError("price file must contain an object/table")
    raw = data.get("models")
    if not isinstance(raw, dict) or not raw:
        raise PriceError("price file needs a non-empty [models] table")
    models: dict[str, ModelPrice] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise PriceError(f"model {name!r}: expected a table of prices")
        values: dict[str, float] = {}
        for key, value in entry.items():
            if key not in PRICE_KEYS:
                raise PriceError(
                    f"model {name!r}: unknown key {key!r} (allowed: {', '.join(PRICE_KEYS)})"
                )
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise PriceError(f"model {name!r}: {key} must be a non-negative number")
            try:
                price = float(value)
            except OverflowError as exc:
                raise PriceError(f"model {name!r}: {key} must be a finite number") from exc
            if not math.isfinite(price):
                raise PriceError(f"model {name!r}: {key} must be a finite number")
            values[key] = price
        models[str(name).lower()] = ModelPrice(**values)
    currency = data.get("currency", "USD")
    return PriceTable(models=models, currency=str(currency))


# --- minimal TOML subset (Python 3.10 has no tomllib) -----------------------

_KEY = r'(?:[A-Za-z0-9_-]+|"[^"]*"|\'[^\']*\')'
_TABLE_RE = re.compile(rf"^\[\s*({_KEY}(?:\s*\.\s*{_KEY})*)\s*\]$")
_KV_RE = re.compile(rf"^({_KEY})\s*=\s*(.+)$")
_PART_RE = re.compile(_KEY)


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
        return token[1:-1]
    return token


def _strip_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _value(text: str) -> Any:
    text = text.strip()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text.replace("_", ""))
    except ValueError:
        pass
    try:
        return float(text.replace("_", ""))
    except ValueError as exc:
        raise PriceError(f"unsupported value: {text!r}") from exc


def parse_toml(text: str) -> dict[str, Any]:
    """Parse the small TOML subset used by price files (tables, scalars, comments)."""
    if sys.version_info >= (3, 11):
        import tomllib

        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise PriceError(str(exc)) from exc
    return _parse_subset(text)


def _parse_subset(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current = root
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw).strip()
        if not line:
            continue
        table = _TABLE_RE.match(line)
        if table:
            current = root
            for part in _PART_RE.findall(table.group(1)):
                current = current.setdefault(_unquote(part), {})
            continue
        pair = _KV_RE.match(line)
        if not pair:
            raise PriceError(f"line {number}: cannot parse {raw.strip()!r}")
        current[_unquote(pair.group(1))] = _value(pair.group(2))
    return root
