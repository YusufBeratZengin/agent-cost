"""agent-cost: token usage and estimated cost reports from local agent logs."""

from __future__ import annotations

from .models import Record
from .pricing import PriceTable, default_prices, load_prices
from .readers import iter_records, read_records
from .report import Row, build_report, filter_records

__version__ = "0.1.0"

__all__ = [
    "PriceTable",
    "Record",
    "Row",
    "__version__",
    "build_report",
    "default_prices",
    "filter_records",
    "iter_records",
    "load_prices",
    "read_records",
]
