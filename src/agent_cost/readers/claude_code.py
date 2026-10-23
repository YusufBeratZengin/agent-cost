"""Reader for Claude Code project session logs (``projects/<dir>/<id>.jsonl``)."""

from __future__ import annotations

from typing import Any

from ..models import Record, parse_timestamp, to_int
from .base import Context


class ClaudeCodeReader:
    name = "claude-code"

    def parse(self, obj: dict[str, Any], ctx: Context) -> Record | None:
        message = obj.get("message")
        if not isinstance(message, dict):
            return None
        usage = message.get("usage")
        if not isinstance(usage, dict):
            return None
        model = message.get("model")
        if not isinstance(model, str) or not model or model.startswith("<"):
            return None  # synthetic placeholder messages carry no real usage
        message_id = message.get("id")
        request_id = obj.get("requestId")
        key = f"{message_id}:{request_id}" if message_id and request_id else None
        session = obj.get("sessionId")
        return Record(
            timestamp=parse_timestamp(obj.get("timestamp")),
            session=session if isinstance(session, str) and session else ctx.file_stem,
            project=ctx.project,
            model=model,
            input_tokens=to_int(usage.get("input_tokens")),
            output_tokens=to_int(usage.get("output_tokens")),
            cache_read_tokens=to_int(usage.get("cache_read_input_tokens")),
            cache_write_tokens=to_int(usage.get("cache_creation_input_tokens")),
            dedupe_key=key,
        )
