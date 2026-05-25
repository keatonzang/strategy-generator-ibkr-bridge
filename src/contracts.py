"""Maps a futures-root symbol to its IBKR exchange code.

The downstream FastAPI endpoint constructs a ContFuture(symbol, exchange)
before calling ib.reqHistoricalData. Unknown symbols surface as 422.
"""

FUTURES_EXCHANGES: dict[str, str] = {
    # CME
    "ES": "CME", "NQ": "CME", "RTY": "CME",
    "MES": "CME", "MNQ": "CME", "M2K": "CME",
    "6E": "CME", "6J": "CME", "6B": "CME", "6A": "CME", "6C": "CME",
    # CBOT
    "YM": "CBOT", "MYM": "CBOT",
    "ZB": "CBOT", "ZN": "CBOT", "ZF": "CBOT", "ZT": "CBOT",
    # NYMEX
    "CL": "NYMEX", "NG": "NYMEX", "RB": "NYMEX", "HO": "NYMEX",
    # COMEX
    "GC": "COMEX", "SI": "COMEX", "HG": "COMEX",
}


class UnknownSymbol(ValueError):
    """The requested symbol isn't in FUTURES_EXCHANGES."""


def resolve_exchange(symbol: str) -> str:
    try:
        return FUTURES_EXCHANGES[symbol.upper()]
    except KeyError as exc:
        raise UnknownSymbol(
            f"Symbol {symbol!r} not in supported futures list"
        ) from exc
