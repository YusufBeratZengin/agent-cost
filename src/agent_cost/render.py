"""Output formats: table, CSV, JSON."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence

from .report import Row

FORMATS = ("table", "csv", "json")


def _headers(dims: Sequence[str]) -> list[str]:
    return [*dims, "requests", "input", "output", "cache_read", "cache_write", "cost"]


def _cost_text(row: Row, currency: str, plain: bool = False) -> str:
    text = f"{row.cost:.4f}" if plain else f"{row.cost:,.2f}"
    if not plain and row.cost and row.cost < 0.01:
        text = f"{row.cost:.4f}"
    if row.unpriced_requests:
        text += "*"
    return text


def render_table(rows: Sequence[Row], total: Row, dims: Sequence[str], currency: str) -> str:
    head = _headers(dims)
    head[-1] = f"cost ({currency})"
    body: list[list[str]] = []
    for row in [*rows, total]:
        keys = list(row.keys) if row is not total else ["TOTAL", *[""] * (len(dims) - 1)]
        body.append(
            [
                *keys,
                f"{row.requests:,}",
                f"{row.input_tokens:,}",
                f"{row.output_tokens:,}",
                f"{row.cache_read_tokens:,}",
                f"{row.cache_write_tokens:,}",
                _cost_text(row, currency),
            ]
        )
    widths = [max(len(head[i]), *(len(line[i]) for line in body)) for i in range(len(head))]
    left = len(dims)

    def fmt(cells: Sequence[str]) -> str:
        parts = [
            cell.ljust(widths[i]) if i < left else cell.rjust(widths[i])
            for i, cell in enumerate(cells)
        ]
        return "  ".join(parts).rstrip()

    rule = "  ".join("-" * w for w in widths)
    lines = [fmt(head), rule, *(fmt(line) for line in body[:-1]), rule, fmt(body[-1])]
    return "\n".join(lines)


def render_csv(rows: Sequence[Row], total: Row, dims: Sequence[str], currency: str) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    head = _headers(dims)
    head[-1] = f"cost_{currency.lower()}"
    head.append("unpriced_requests")
    writer.writerow(head)
    for row in [*rows, total]:
        keys = list(row.keys) if row is not total else ["TOTAL", *[""] * (len(dims) - 1)]
        writer.writerow(
            [
                *keys,
                row.requests,
                row.input_tokens,
                row.output_tokens,
                row.cache_read_tokens,
                row.cache_write_tokens,
                f"{row.cost:.6f}",
                row.unpriced_requests,
            ]
        )
    return buf.getvalue().rstrip("\n")


def _row_dict(row: Row) -> dict[str, int | float]:
    return {
        "requests": row.requests,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "cache_read_tokens": row.cache_read_tokens,
        "cache_write_tokens": row.cache_write_tokens,
        "total_tokens": row.total_tokens,
        "cost": round(row.cost, 6),
        "unpriced_requests": row.unpriced_requests,
    }


def render_json(
    rows: Sequence[Row], total: Row, dims: Sequence[str], currency: str, builtin_prices: bool
) -> str:
    payload = {
        "group_by": list(dims),
        "currency": currency,
        "prices": "builtin-example" if builtin_prices else "user",
        "rows": [{**dict(zip(dims, row.keys, strict=True)), **_row_dict(row)} for row in rows],
        "total": _row_dict(total),
    }
    return json.dumps(payload, indent=2)
