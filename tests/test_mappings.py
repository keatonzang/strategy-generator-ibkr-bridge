import pytest

from src.mappings import (
    BAR_SIZES, LOOKBACKS,
    UnknownBarSize, UnknownLookback, UnsupportedCombo,
    resolve_bar_size, resolve_lookback, validate_combo,
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


# -- Combo limits (single-request IBKR duration ceilings, measured 2026-05-29).
# Sub-hourly bars cannot be served for these lookbacks in one reqHistoricalData
# call; IBKR silently stalls and the bridge times out at 30 s. validate_combo
# rejects them up front with an actionable error instead.

def test_validate_combo_allows_proven_good_combos():
    # These returned data end-to-end against the paper account.
    validate_combo("1h", "1mo")
    validate_combo("1d", "5y")
    validate_combo("1d", "1mo")
    validate_combo("1h", "3mo")  # used by the happy-path test in test_main


@pytest.mark.parametrize(
    "bar,lookback",
    [
        ("1m", "1mo"),   # 1-min unusable at any offered lookback
        ("1m", "1y"),
        ("5m", "1mo"),   # 5-min unusable at any offered lookback
        ("5m", "3mo"),
        ("15m", "3mo"),  # 15-min stalls from 3mo up
        ("15m", "1y"),
    ],
)
def test_validate_combo_rejects_over_limit(bar, lookback):
    with pytest.raises(UnsupportedCombo) as exc:
        validate_combo(bar, lookback)
    # message should name the bar size and point the user at a remedy
    msg = str(exc.value)
    assert bar in msg
    assert "larger bar" in msg or "shorter" in msg
