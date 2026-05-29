"""Allowed bar sizes and lookbacks, plus their IBKR API duration strings."""

BAR_SIZES: dict[str, str] = {
    "1m": "1 min",
    "5m": "5 mins",
    "15m": "15 mins",
    "1h": "1 hour",
    "1d": "1 day",
}

LOOKBACKS: dict[str, str] = {
    "1mo": "30 D",
    "3mo": "90 D",
    "6mo": "180 D",
    "1y": "1 Y",
    "2y": "2 Y",
    "5y": "5 Y",
}


class UnknownBarSize(ValueError):
    pass


class UnknownLookback(ValueError):
    pass


class UnsupportedCombo(ValueError):
    """The (barSize, lookback) pair asks for more data than one request serves."""


# Approximate bars produced per calendar day by bar size, assuming ~23 h futures
# sessions. Only used to estimate a request's volume for the guardrail below.
_BARS_PER_DAY: dict[str, int] = {"1m": 1380, "5m": 276, "15m": 92, "1h": 23, "1d": 1}
_LOOKBACK_DAYS: dict[str, int] = {
    "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
}

# IBKR silently stalls (never sends historicalDataEnd, no error) when a single
# reqHistoricalData asks for more bars than the account/data-farm will serve in
# one shot; the bridge then times out at 30 s with an opaque 504. Measured on the
# paper account 2026-05-29: ~1.8k bars (1d/5y) returns, ~8k+ (5m/1mo) stalls, so
# 5000 is a conservative single-request cap. Chunking (future work) will lift it.
MAX_BARS_PER_REQUEST = 5000


def estimate_bar_count(bar_key: str, lookback_key: str) -> int:
    return _BARS_PER_DAY[bar_key] * _LOOKBACK_DAYS[lookback_key]


def validate_combo(bar_key: str, lookback_key: str) -> None:
    """Reject combos that would exceed IBKR's single-request volume up front,
    so the caller gets an instant actionable error instead of a 30 s stall."""
    est = estimate_bar_count(bar_key, lookback_key)
    if est > MAX_BARS_PER_REQUEST:
        raise UnsupportedCombo(
            f"{bar_key}/{lookback_key} needs ~{est:,} bars, over the "
            f"{MAX_BARS_PER_REQUEST:,}-bar single-request limit. "
            f"Use a larger bar size or a shorter lookback."
        )


def resolve_bar_size(key: str) -> str:
    try:
        return BAR_SIZES[key]
    except KeyError as exc:
        raise UnknownBarSize(
            f"barSize {key!r} not in {sorted(BAR_SIZES)}"
        ) from exc


def resolve_lookback(key: str) -> str:
    try:
        return LOOKBACKS[key]
    except KeyError as exc:
        raise UnknownLookback(
            f"lookback {key!r} not in {sorted(LOOKBACKS)}"
        ) from exc
