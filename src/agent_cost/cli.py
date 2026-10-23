"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .pricing import PriceError, default_prices, default_prices_toml, load_prices
from .readers import READERS, read_records
from .render import FORMATS, render_csv, render_json, render_table
from .report import DIMENSIONS, build_report, filter_records, parse_day

BUILTIN_WARNING = (
    "note: using built-in EXAMPLE prices; verify them yourself and pass --prices FILE."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-cost",
        description="Token usage and estimated cost from local AI coding agent logs (JSONL).",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="log files or folders to scan")
    parser.add_argument(
        "-r",
        "--reader",
        default="auto",
        choices=["auto", *sorted(READERS)],
        help="log format (default: auto-detect per line)",
    )
    parser.add_argument(
        "-b",
        "--by",
        default="day",
        help=f"comma-separated grouping: {', '.join(DIMENSIONS)} (default: day)",
    )
    parser.add_argument("-p", "--prices", type=Path, help="price table, TOML or JSON")
    parser.add_argument("-f", "--format", default="table", choices=FORMATS, dest="fmt")
    parser.add_argument("--since", help="first day to include, YYYY-MM-DD (UTC)")
    parser.add_argument("--until", help="last day to include, YYYY-MM-DD (UTC)")
    parser.add_argument("--project", help="keep projects whose name contains this text")
    parser.add_argument("--model", help="keep models whose name contains this text")
    parser.add_argument(
        "--print-default-prices",
        action="store_true",
        help="print the built-in example price table as TOML and exit",
    )
    parser.add_argument("-V", "--version", action="version", version=f"agent-cost {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_default_prices:
        print(default_prices_toml())
        return 0
    if not args.paths:
        parser.error("give at least one log file or folder")

    dims = [d.strip() for d in args.by.split(",") if d.strip()]
    try:
        since = parse_day(args.since) if args.since else None
        until = parse_day(args.until) if args.until else None
        prices = load_prices(args.prices) if args.prices else default_prices()
        records = read_records(args.paths, args.reader)
        records = filter_records(records, since, until, args.project, args.model)
        rows, total = build_report(records, prices, dims)
    except (ValueError, PriceError, FileNotFoundError) as exc:
        print(f"agent-cost: error: {exc}", file=sys.stderr)
        return 2

    if args.fmt == "csv":
        out = render_csv(rows, total, dims, prices.currency)
    elif args.fmt == "json":
        out = render_json(rows, total, dims, prices.currency, prices.builtin)
    else:
        out = render_table(rows, total, dims, prices.currency)
    print(out)

    if args.fmt == "table":
        if total.unpriced_requests:
            print(
                f"* {total.unpriced_requests} request(s) use a model missing from the price "
                "table and are not included in cost.",
                file=sys.stderr,
            )
        if prices.builtin:
            print(BUILTIN_WARNING, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
