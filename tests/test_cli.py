from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_cost.cli import main

PRICES = (
    '[models."claude-sonnet"]\ninput = 1\noutput = 2\n'
    '[models."claude-opus"]\ninput = 5\noutput = 10\n'
)


def test_table_default_warns_about_builtin_prices(
    logs: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(logs)]) == 0
    cap = capsys.readouterr()
    assert "2026-01-10" in cap.out and "TOTAL" in cap.out
    assert "EXAMPLE prices" in cap.err


def test_json_csv_with_price_file(
    logs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "p.toml"
    p.write_text(PRICES, encoding="utf-8")
    assert main([str(logs), "-p", str(p), "-f", "json", "--by", "model"]) == 0
    cap = capsys.readouterr()
    data = json.loads(cap.out)
    assert data["total"]["requests"] == 3 and data["prices"] == "user"
    assert cap.err == ""
    assert main([str(logs), "-p", str(p), "-f", "csv", "--since", "2026-01-12"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("day,requests") and out[1].startswith("2026-01-12,1,")


def test_unpriced_note(logs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"models": {"claude-sonnet": {"input": 1}}}), encoding="utf-8")
    assert main([str(logs), "-p", str(p)]) == 0
    assert "missing from the price table" in capsys.readouterr().err


def test_filters_via_cli(logs: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(logs), "--project", "alpha", "--until", "2026-01-10", "-f", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["total"]["requests"] == 1
    assert main([str(logs), "--model", "opus", "-f", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["total"]["requests"] == 1


@pytest.mark.parametrize(
    "args",
    [["--since", "yesterday"], ["--by", "week"], ["-p", "missing.toml"]],
)
def test_errors_exit_2(logs: Path, args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(logs), *args]) == 2
    assert "agent-cost: error:" in capsys.readouterr().err


def test_missing_path_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "nope")]) == 2
    assert "no such file" in capsys.readouterr().err


def test_no_paths_is_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_print_default_prices_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--print-default-prices"]) == 0
    assert "EXAMPLE" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "agent-cost" in capsys.readouterr().out


def test_module_entry_point(logs: Path) -> None:
    src = str(Path(__file__).resolve().parents[1] / "src")
    env = {**os.environ, "PYTHONPATH": src}
    proc = subprocess.run(
        [sys.executable, "-m", "agent_cost", str(logs), "-f", "csv"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.startswith("day,requests")
