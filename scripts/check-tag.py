"""Fail unless the given git tag (vX.Y.Z) equals the version in pyproject.toml."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    text = Path(__file__).resolve().parents[1].joinpath("pyproject.toml").read_text("utf-8")
    match = re.search(r'^version = "(.+?)"', text, re.MULTILINE)
    if match is None:
        print("version not found in pyproject.toml")
        return 1
    expected = f"v{match.group(1)}"
    if len(sys.argv) != 2 or sys.argv[1] != expected:
        print(f"tag mismatch: expected {expected}, got {sys.argv[1:]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
