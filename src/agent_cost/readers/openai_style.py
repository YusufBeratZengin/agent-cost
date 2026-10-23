"""Reader for generic OpenAI-style usage lines.

Understands ``prompt_tokens`` / ``completion_tokens`` (chat completions) and
``input_tokens`` / ``output_tokens`` (responses API). OpenAI reports cached
prompt tokens inside the prompt total, so they are subtracted from the input
count here to keep the four buckets disjoint.
"""

from __future__ import annotations

from typing import Any

from ..models import Record, parse_timestamp, to_int
from .base import Context

_WRAPPERS = ("response", "body", "result")


class OpenAIStyleReader:
    name = "openai"

    def parse(self, obj: dict[str, Any], ctx: Context) -> Record | None:
        data = self._unwrap(obj)
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        if "prompt_tokens" in usage or "completion_tokens" in usage:
            prompt = to_int(usage.get("prompt_tokens"))
            output = to_int(usage.get("completion_tokens"))
            details = usage.get("prompt_tokens_details")
        elif "input_tokens" in usage or "output_tokens" in usage:
            prompt = to_int(usage.get("input_tokens"))
            output = to_int(usage.get("output_tokens"))
            details = usage.get("input_tokens_details")
        else:
            return None
        cached = to_int(details.get("cached_tokens")) if isinstance(details, dict) else 0
        cached = min(cached, prompt)
        model = data.get("model") or obj.get("model")
        session = (
            obj.get("session_id")
            or obj.get("conversation_id")
            or data.get("session_id")
            or ctx.file_stem
        )
        stamp = (
            obj.get("timestamp")
            or data.get("created_at")
            or data.get("created")
            or obj.get("created")
        )
        ident = data.get("id") or obj.get("id")
        return Record(
            timestamp=parse_timestamp(stamp),
            session=str(session),
            project=ctx.project,
            model=model if isinstance(model, str) and model else "unknown",
            input_tokens=prompt - cached,
            output_tokens=output,
            cache_read_tokens=cached,
            cache_write_tokens=0,
            dedupe_key=str(ident) if ident else None,
        )

    @staticmethod
    def _unwrap(obj: dict[str, Any]) -> dict[str, Any]:
        if isinstance(obj.get("usage"), dict):
            return obj
        for name in _WRAPPERS:
            inner = obj.get(name)
            if isinstance(inner, dict):
                if isinstance(inner.get("usage"), dict):
                    return inner
                body = inner.get("body")
                if isinstance(body, dict) and isinstance(body.get("usage"), dict):
                    return body
        return obj
