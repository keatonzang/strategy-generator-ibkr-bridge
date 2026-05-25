"""Format ib_insync BarData → CSV string matching the Lambda's expected columns."""

from datetime import datetime
from typing import Iterable, Protocol


class Bar(Protocol):
    """Structural subset of ib_insync.BarData we depend on.

    ib_insync returns `date` as a `datetime` for intraday bars and a
    `date` for daily bars; both have `.strftime` only when `datetime`.
    """
    date: object
    open: float
    high: float
    low: float
    close: float
    volume: float


CSV_HEADER = "datetime,Open,High,Low,Close,volume,openinterest"


def _format_dt(d: object) -> str:
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M:%S")
    # `date` (no time component) → midnight
    return f"{d} 00:00:00"


def bars_to_csv(bars: Iterable[Bar]) -> str:
    rows = [CSV_HEADER]
    for b in bars:
        rows.append(
            f"{_format_dt(b.date)},{b.open},{b.high},{b.low},{b.close},{int(b.volume)},0"
        )
    return "\n".join(rows) + ("\n" if len(rows) > 1 else "")
