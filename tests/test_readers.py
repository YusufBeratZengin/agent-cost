from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from agent_cost.models import Record, parse_timestamp, to_int
from agent_cost.readers import READERS, find_files, read_records, register
from agent_cost.readers.base import Context

from .conftest import claude_line, jdump, write_lines


def test_claude_reader_reads_usage_and_projects(logs: Path) -> None:
    recs = read_records([logs])
    assert len(recs) == 3
    first = recs[0]
    assert (first.input_tokens, first.output_tokens) == (100, 50)
    assert (first.cache_read_tokens, first.cache_write_tokens) == (1000, 200)
    assert first.project == "-fake-alpha"
    assert first.session == "s1"
    assert first.day == "2026-01-10"
    assert {r.project for r in recs} == {"-fake-alpha", "-fake-beta"}


def test_streamed_duplicates_counted_once_keeping_last(tmp_path: Path) -> None:
    f = write_lines(
        tmp_path / "a.jsonl",
        [
            claude_line("2026-01-01T00:00:00Z", out=1, msg_id="m", req_id="r"),
            claude_line("2026-01-01T00:00:01Z", out=40, msg_id="m", req_id="r"),
        ],
    )
    recs = read_records([f])
    assert len(recs) == 1
    assert recs[0].output_tokens == 40


def test_synthetic_model_and_missing_usage_skipped(tmp_path: Path) -> None:
    f = write_lines(
        tmp_path / "a.jsonl",
        [
            claude_line("2026-01-01T00:00:00Z", model="<synthetic>", out=5),
            jdump({"message": {"model": "x"}}),
            jdump({"message": "text"}),
            jdump([1, 2]),
            "",
        ],
    )
    assert read_records([f]) == []


def test_openai_chat_style_subtracts_cached(tmp_path: Path) -> None:
    f = write_lines(
        tmp_path / "chat.jsonl",
        [
            jdump(
                {
                    "id": "c1",
                    "model": "gpt-fake",
                    "created": 1767225600,
                    "session_id": "chat-a",
                    "usage": {
                        "prompt_tokens": 1000,
                        "completion_tokens": 200,
                        "prompt_tokens_details": {"cached_tokens": 400},
                    },
                }
            )
        ],
    )
    (rec,) = read_records([f])
    assert (rec.input_tokens, rec.cache_read_tokens, rec.output_tokens) == (600, 400, 200)
    assert rec.session == "chat-a"
    assert rec.day == "2026-01-01"
    assert rec.project == tmp_path.name


def test_openai_responses_style_and_wrapped(tmp_path: Path) -> None:
    f = write_lines(
        tmp_path / "r.jsonl",
        [
            jdump(
                {
                    "response": {
                        "id": "x",
                        "model": "gpt-fake",
                        "usage": {
                            "input_tokens": 50,
                            "output_tokens": 7,
                            "input_tokens_details": {"cached_tokens": 900},
                        },
                    }
                }
            ),
            jdump(
                {
                    "response": {
                        "body": {
                            "model": "gpt-fake",
                            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
                        }
                    }
                }
            ),
            jdump({"usage": {"total": 3}}),
            jdump({"response": {"usage": "nope"}}),
        ],
    )
    recs = read_records([f], "openai")
    assert len(recs) == 2
    assert recs[0].cache_read_tokens == 50 and recs[0].input_tokens == 0  # cached is capped
    assert recs[1].model == "gpt-fake" and recs[1].session == "r"


def test_openai_missing_model_is_unknown(tmp_path: Path) -> None:
    f = write_lines(tmp_path / "m.jsonl", [jdump({"usage": {"prompt_tokens": 1}})])
    assert read_records([f])[0].model == "unknown"


def test_explicit_reader_and_unknown_reader(tmp_path: Path) -> None:
    f = write_lines(tmp_path / "a.jsonl", [claude_line("2026-01-01T00:00:00Z", inp=1)])
    assert len(read_records([f], "claude-code")) == 1
    assert read_records([f], "openai") == []
    with pytest.raises(ValueError, match="unknown reader"):
        read_records([f], "nope")


def test_find_files_missing_and_suffix(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("hi")
    (tmp_path / "y.ndjson").write_text("{}\n")
    assert [p.name for p in find_files(tmp_path)] == ["y.ndjson"]
    with pytest.raises(FileNotFoundError):
        find_files(tmp_path / "missing")


def test_custom_reader_plugin(tmp_path: Path) -> None:
    class Plain:
        name = "plain-test"

        def parse(self, obj: dict[str, object], ctx: Context) -> Record | None:
            if "tok" not in obj:
                return None
            return Record(None, ctx.file_stem, ctx.project, "m", input_tokens=int(str(obj["tok"])))

    register(Plain())
    try:
        f = write_lines(tmp_path / "p.jsonl", [jdump({"tok": 9})])
        (rec,) = read_records([f], "plain-test")
        assert rec.input_tokens == 9 and rec.day == "unknown"
    finally:
        READERS.pop("plain-test")


def test_parse_helpers() -> None:
    assert to_int(True) == 0 and to_int("5") == 0 and to_int(-3) == 0 and to_int(4.9) == 4
    offset = parse_timestamp("2026-01-01T02:00:00+02:00")
    assert offset is not None and offset.hour == 0 and offset.tzinfo == timezone.utc
    naive = parse_timestamp("2026-01-01T00:00:00")
    assert naive is not None and naive.tzinfo == timezone.utc
    assert parse_timestamp(1767225600000) == parse_timestamp(1767225600)
    assert parse_timestamp("garbage") is None
    assert parse_timestamp(True) is None and parse_timestamp(None) is None
    assert parse_timestamp(1e30) is None and parse_timestamp("") is None
    assert parse_timestamp([]) is None
