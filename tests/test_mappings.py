import pytest

from src.mappings import (
    BAR_SIZES, LOOKBACKS,
    UnknownBarSize, UnknownLookback,
    resolve_bar_size, resolve_lookback,
)


def test_bar_size_keys_are_the_allowed_set():
    assert set(BAR_SIZES) == {"1m", "5m", "15m", "1h", "1d"}


def test_lookback_keys_are_the_allowed_set():
    assert set(LOOKBACKS) == {"1mo", "3mo", "6mo", "1y", "2y", "5y"}


def test_resolve_bar_size_maps_to_ibkr_string():
    assert resolve_bar_size("1h") == "1 hour"
    assert resolve_bar_size("5m") == "5 mins"


def test_resolve_lookback_maps_to_ibkr_string():
    assert resolve_lookback("2y") == "2 Y"
    assert resolve_lookback("3mo") == "90 D"


def test_unknown_bar_size_raises():
    with pytest.raises(UnknownBarSize):
        resolve_bar_size("4h")


def test_unknown_lookback_raises():
    with pytest.raises(UnknownLookback):
        resolve_lookback("100y")
