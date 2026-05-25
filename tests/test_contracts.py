import pytest

from src.contracts import resolve_exchange, UnknownSymbol


def test_known_es_resolves_to_cme():
    assert resolve_exchange("ES") == "CME"


def test_known_cl_resolves_to_nymex():
    assert resolve_exchange("CL") == "NYMEX"


def test_lowercase_is_normalized():
    assert resolve_exchange("gc") == "COMEX"


def test_unknown_symbol_raises_with_message():
    with pytest.raises(UnknownSymbol, match="ZZZ"):
        resolve_exchange("ZZZ")
