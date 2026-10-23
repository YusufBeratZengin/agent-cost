from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def claude_line(
    ts: str,
    model: str = "claude-sonnet-fake",
    inp: int = 0,
    out: int = 0,
    cread: int = 0,
    cwrite: int = 0,
    msg_id: str = "msg_1",
    req_id: str = "req_1",
    session: str = "sess-1",
) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "sessionId": session,
            "timestamp": ts,
            "requestId": req_id,
            "message": {
                "id": msg_id,
                "model": model,
                "role": "assistant",
                "content": [{"type": "text", "text": "synthetic reply"}],
                "usage": {
                    "input_tokens": inp,
                    "output_tokens": out,
                    "cache_read_input_tokens": cread,
                    "cache_creation_input_tokens": cwrite,
                },
            },
        }
    )


def write_lines(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def jdump(obj: Any) -> str:
    return json.dumps(obj)


@pytest.fixture
def logs(tmp_path: Path) -> Path:
    """Synthetic Claude-Code-style tree with two fake projects."""
    root = tmp_path / "projects"
    write_lines(
        root / "-fake-alpha" / "s1.jsonl",
        [
            jdump({"type": "user", "message": {"role": "user", "content": "hi"}}),
            claude_line(
                "2026-01-10T10:00:00Z",
                inp=100,
                out=50,
                cread=1000,
                cwrite=200,
                msg_id="m1",
                req_id="r1",
                session="s1",
            ),
            claude_line(
                "2026-01-11T23:59:59Z", inp=10, out=5, msg_id="m2", req_id="r2", session="s1"
            ),
            "not json at all",
        ],
    )
    write_lines(
        root / "-fake-beta" / "s2.jsonl",
        [
            claude_line(
                "2026-01-12T00:00:00Z",
                model="claude-opus-fake",
                inp=1_000_000,
                out=1_000_000,
                msg_id="m3",
                req_id="r3",
                session="s2",
            ),
        ],
    )
    return root
