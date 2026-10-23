"""Render docs/demo.svg from the real CLI output on the synthetic examples/.

Usage: python scripts/make-demo.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ["examples/sessions", "examples/openai", "--prices", "examples/prices.toml"],
    ["examples", "--by", "project,model", "--prices", "examples/prices.toml"],
]


def run(args: list[str]) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "agent_cost", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.rstrip("\n")


def main() -> None:
    lines: list[tuple[str, str]] = []
    for i, args in enumerate(COMMANDS):
        if i:
            lines.append(("", "plain"))
        lines.append(("$ agent-cost " + " ".join(args), "cmd"))
        lines.extend((row, "out") for row in run(args).splitlines())
    width_chars = max(len(text) for text, _ in lines)
    char_w, line_h, pad = 8.4, 20, 20
    width = int(width_chars * char_w + pad * 2)
    height = len(lines) * line_h + pad * 2 + 24
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="agent-cost terminal output">',
        f'<rect width="{width}" height="{height}" rx="8" fill="#0d1117"/>',
        '<circle cx="20" cy="16" r="5" fill="#ff5f56"/>'
        '<circle cx="38" cy="16" r="5" fill="#ffbd2e"/>'
        '<circle cx="56" cy="16" r="5" fill="#27c93f"/>',
        '<g font-family="Consolas, Menlo, \'DejaVu Sans Mono\', monospace" font-size="14" '
        'xml:space="preserve">',
    ]
    colors = {"cmd": "#7ee787", "out": "#c9d1d9", "plain": "#c9d1d9"}
    for n, (text, kind) in enumerate(lines):
        y = 24 + pad + 14 + n * line_h
        out.append(f'<text x="{pad}" y="{y}" fill="{colors[kind]}">{escape(text)}</text>')
    out.append("</g></svg>")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "demo.svg").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote docs/demo.svg")


if __name__ == "__main__":
    main()
