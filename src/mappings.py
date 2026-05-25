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
