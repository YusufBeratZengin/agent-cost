from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

from agent_cost import build_report, default_prices, filter_records, load_prices, read_records
from agent_cost.models import Record
from agent_cost.pricing import (
    ModelPrice,
    PriceError,
    PriceTable,
    _parse_subset,
    default_prices_toml,
    parse_toml,
    table_from_dict,
)
from agent_cost.render import render_csv, render_json, render_table
from agent_cost.report import parse_day

TOML = """
# comment
currency = "EUR"   # trailing

[models."claude-sonnet"]
input = 3.0
output = 15
cache_read = 0.3
cache_write = 3.75

[models.gpt-x]
input = 1
"""


def rec(model: str = "claude-sonnet-fake", **kw: int) -> Record:
    return Record(None, "s", "p", model, **kw)


def test_cost_math_and_matching() -> None:
    table = PriceTable(
        {"claude-sonnet": ModelPrice(3.0, 15.0, 0.3, 3.75), "claude": ModelPrice(1.0, 1.0)}
    )
    r = rec(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    assert table.cost(r) == pytest.approx(3.0 + 15.0 + 0.3 + 3.75)
    assert table.lookup("CLAUDE-SONNET-9") is table.models["claude-sonnet"]  # longest prefix
    assert table.lookup("my-claude-thing") is table.models["claude"]  # substring
    assert table.cost(rec(model="other")) is None


@pytest.mark.skipif(sys.version_info < (3, 11), reason="needs tomllib")
def test_toml_subset_parser_matches_tomllib() -> None:
    import tomllib

    assert _parse_subset(TOML) == tomllib.loads(TOML)


def test_toml_subset_errors_and_values() -> None:
    with pytest.raises(PriceError):
        _parse_subset("this is not toml")
    with pytest.raises(PriceError):
        _parse_subset("a = [1, 2]")
    assert _parse_subset("a = true\nb = 'x'\nc = \"q # r\"") == {"a": True, "b": "x", "c": "q # r"}


def test_parse_toml_reports_decode_errors() -> None:
    with pytest.raises(PriceError):
        parse_toml("a = = 1")


def test_load_prices_toml_and_json(tmp_path: Path) -> None:
    t = tmp_path / "p.toml"
    t.write_text('currency = "EUR"\n[models."M-1"]\ninput = 2\noutput = 4\n', encoding="utf-8")
    table = load_prices(t)
    assert table.currency == "EUR" and not table.builtin
    assert table.models["m-1"].output == 4.0
    j = tmp_path / "p.json"
    j.write_text(json.dumps({"models": {"a": {"input": 1}}}), encoding="utf-8")
    assert load_prices(j).models["a"].input == 1.0


@pytest.mark.parametrize(
    "data",
    [
        [],
        {},
        {"models": {}},
        {"models": {"a": 1}},
        {"models": {"a": {"bogus": 1}}},
        {"models": {"a": {"input": -1}}},
        {"models": {"a": {"input": "3"}}},
        {"models": {"a": {"input": True}}},
    ],
)
def test_bad_price_tables(data: object) -> None:
    with pytest.raises(PriceError):
        table_from_dict(data)


def test_load_prices_errors(tmp_path: Path) -> None:
    with pytest.raises(PriceError, match="cannot read"):
        load_prices(tmp_path / "missing.toml")
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    with pytest.raises(PriceError, match="invalid"):
        load_prices(bad)


def test_default_table_is_flagged_and_dumpable() -> None:
    assert default_prices().builtin
    text = default_prices_toml()
    assert "EXAMPLE" in text
    assert table_from_dict(parse_toml(text)).models.keys() == default_prices().models.keys()


def test_filters(logs: Path) -> None:
    recs = read_records([logs])
    assert len(filter_records(recs, since=date(2026, 1, 11))) == 2
    assert len(filter_records(recs, until=date(2026, 1, 10))) == 1
    assert len(filter_records(recs, date(2026, 1, 11), date(2026, 1, 11))) == 1  # inclusive end
    assert len(filter_records(recs, project="BETA")) == 1
    assert len(filter_records(recs, model="opus")) == 1
    undated = [rec()]
    assert filter_records(undated, since=date(2020, 1, 1)) == []
    assert filter_records(undated) == undated


def test_parse_day() -> None:
    assert parse_day("2026-02-03") == date(2026, 2, 3)
    with pytest.raises(ValueError, match="invalid date"):
        parse_day("03/02/2026")


def test_report_grouping_and_totals(logs: Path) -> None:
    table = PriceTable(
        {
            "claude-sonnet": ModelPrice(10.0, 20.0, 1.0, 2.0),
            "claude-opus": ModelPrice(100.0, 200.0),
        }
    )
    records = read_records([logs])
    rows, total = build_report(records, table, ["day"])
    assert [r.keys[0] for r in rows] == ["2026-01-10", "2026-01-11", "2026-01-12"]
    assert total.requests == 3
    assert total.input_tokens == 100 + 10 + 1_000_000
    assert total.cost == pytest.approx(
        (100 * 10 + 50 * 20 + 1000 * 1 + 200 * 2 + 10 * 10 + 5 * 20) / 1e6 + 300.0
    )
    by_model, _ = build_report(records, table, ["model"])
    assert by_model[0].keys == ("claude-opus-fake",)  # highest cost first
    multi, _ = build_report(records, table, ["project", "model"])
    assert len(multi) == 2 and multi[0].keys == ("-fake-beta", "claude-opus-fake")
    sessions, _ = build_report(records, table, ["session"])
    assert {r.keys[0] for r in sessions} == {"s1", "s2"}


def test_unpriced_models_tracked() -> None:
    table = PriceTable({"x": ModelPrice()})
    rows, total = build_report([rec(model="mystery", input_tokens=5)], table)
    assert total.unpriced_requests == 1 and rows[0].cost == 0.0


def test_bad_dimensions() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_report([], default_prices(), [])
    with pytest.raises(ValueError, match="unknown dimension"):
        build_report([], default_prices(), ["week"])


def test_renderers(logs: Path) -> None:
    table = PriceTable({"claude-sonnet": ModelPrice(10.0, 20.0)}, currency="EUR")
    dims = ["project", "model"]
    rows, total = build_report(read_records([logs]), table, dims)
    text = render_table(rows, total, dims, "EUR")
    assert "cost (EUR)" in text and "TOTAL" in text and "1,000,110" in text and "*" in text
    lines = render_csv(rows, total, dims, "EUR").splitlines()
    assert lines[0].startswith("project,model,requests") and "cost_eur" in lines[0]
    assert lines[-1].startswith("TOTAL,,")
    data = json.loads(render_json(rows, total, dims, "EUR", False))
    assert data["prices"] == "user" and data["rows"][0]["project"]
    assert data["total"]["requests"] == 3
    assert json.loads(render_json(rows, total, dims, "USD", True))["prices"] == "builtin-example"


def test_small_cost_shows_more_digits() -> None:
    rows, total = build_report([rec(input_tokens=100)], PriceTable({"claude": ModelPrice(3.0)}))
    assert "0.0003" in render_table(rows, total, ["day"], "USD")
