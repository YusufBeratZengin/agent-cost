"""Reader registry and file walking."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from ..models import Record
from .base import Context, Reader
from .claude_code import ClaudeCodeReader
from .openai_style import OpenAIStyleReader

READERS: dict[str, Reader] = {}


def register(reader: Reader) -> None:
    """Add a reader plugin. A later registration with the same name replaces it."""
    READERS[reader.name] = reader


register(ClaudeCodeReader())
register(OpenAIStyleReader())

SUFFIXES = (".jsonl", ".ndjson")


def find_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in SUFFIXES)
    raise FileNotFoundError(f"no such file or directory: {path}")


def _project_for(file: Path, root: Path) -> str:
    if root.is_dir():
        parts = file.relative_to(root).parts
        if len(parts) > 1:
            return parts[0]
        return root.resolve().name
    return file.resolve().parent.name


def iter_records(paths: Iterable[Path], reader: str = "auto") -> Iterator[Record]:
    """Yield records from every JSONL file under ``paths``.

    Malformed lines are skipped. Records sharing a ``dedupe_key`` (streamed
    messages are logged more than once) are counted once, keeping the last
    occurrence.
    """
    if reader != "auto" and reader not in READERS:
        raise ValueError(f"unknown reader {reader!r}; available: {', '.join(sorted(READERS))}")
    chosen = list(READERS.values()) if reader == "auto" else [READERS[reader]]
    keyed: dict[str, int] = {}
    out: list[Record] = []
    for root in paths:
        for file in find_files(root):
            ctx = Context(project=_project_for(file, root), file_stem=file.stem)
            with file.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    for candidate in chosen:
                        rec = candidate.parse(obj, ctx)
                        if rec is None:
                            continue
                        if rec.dedupe_key is not None:
                            if rec.dedupe_key in keyed:
                                out[keyed[rec.dedupe_key]] = rec
                                break
                            keyed[rec.dedupe_key] = len(out)
                        out.append(rec)
                        break
    yield from out


def read_records(paths: Iterable[Path], reader: str = "auto") -> list[Record]:
    return list(iter_records(paths, reader))


__all__ = ["READERS", "Context", "Reader", "find_files", "iter_records", "read_records", "register"]
