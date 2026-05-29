from datetime import datetime
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src import ibkr_client, main


@dataclass
class FakeBar:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    """Force every test to start with no IB connection cached."""
    yield
    # Reset module-level state between tests
    import asyncio
    asyncio.run(ibkr_client.reset_for_tests())


def test_health_before_connect_returns_false():
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": True, "ibkrConnected": False}


def test_historical_rejects_unknown_symbol(monkeypatch):
    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ZZZ", "barSize": "1h", "lookback": "3mo"})
    assert r.status_code == 422
    assert "ZZZ" in r.json()["detail"]


def test_historical_rejects_unknown_bar_size():
    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "4h", "lookback": "3mo"})
    # pydantic rejects values outside the Literal, surfacing as 422
    assert r.status_code == 422


def test_historical_happy_path_returns_csv(monkeypatch):
    fake_ib = MagicMock()
    fake_ib.isConnected.return_value = True
    fake_ib.qualifyContractsAsync = AsyncMock(return_value=None)
    fake_ib.reqHistoricalDataAsync = AsyncMock(return_value=[
        FakeBar(datetime(2024, 1, 2, 9, 30), 4783.5, 4790.25, 4780.0, 4787.75, 123456),
        FakeBar(datetime(2024, 1, 2, 10, 30), 4787.75, 4795.0, 4785.0, 4792.0, 100000),
    ])

    async def fake_get_ib():
        return fake_ib

    monkeypatch.setattr(main, "get_ib", fake_get_ib)

    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "1h", "lookback": "3mo"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == "ES-1h-3mo.csv"
    assert body["barCount"] == 2
    assert body["csv"].splitlines()[0] == "datetime,Open,High,Low,Close,volume,openinterest"


def test_historical_zero_bars_returns_422(monkeypatch):
    fake_ib = MagicMock()
    fake_ib.isConnected.return_value = True
    fake_ib.qualifyContractsAsync = AsyncMock(return_value=None)
    fake_ib.reqHistoricalDataAsync = AsyncMock(return_value=[])

    async def fake_get_ib():
        return fake_ib

    monkeypatch.setattr(main, "get_ib", fake_get_ib)

    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "1h", "lookback": "3mo"})
    assert r.status_code == 422
    assert "0 bars" in r.json()["detail"]


def test_historical_connect_failure_returns_503(monkeypatch):
    async def boom():
        raise ConnectionRefusedError("nope")

    monkeypatch.setattr(main, "get_ib", boom)

    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "1h", "lookback": "3mo"})
    assert r.status_code == 503
    assert "IBKR Gateway unreachable" in r.json()["detail"]


def test_historical_rejects_over_limit_combo_before_calling_ib(monkeypatch):
    # 1m/1y is far over the single-request bar limit -> 400 without touching IB.
    called = False

    async def fake_get_ib():
        nonlocal called
        called = True
        return MagicMock()

    monkeypatch.setattr(main, "get_ib", fake_get_ib)

    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "1m", "lookback": "1y"})
    assert r.status_code == 400
    assert "larger bar size" in r.json()["detail"]
    assert called is False  # rejected before any IB call


def test_historical_timeout_drops_connection_and_returns_504(monkeypatch):
    import asyncio

    fake_ib = MagicMock()
    fake_ib.isConnected.return_value = True
    fake_ib.qualifyContractsAsync = AsyncMock(return_value=None)

    async def never_returns(*args, **kwargs):
        await asyncio.sleep(1)  # longer than the patched timeout below

    fake_ib.reqHistoricalDataAsync = AsyncMock(side_effect=never_returns)

    async def fake_get_ib():
        return fake_ib

    dropped = False

    async def fake_drop():
        nonlocal dropped
        dropped = True

    monkeypatch.setattr(main, "get_ib", fake_get_ib)
    monkeypatch.setattr(main, "drop_connection", fake_drop)
    monkeypatch.setattr(main, "HISTORICAL_TIMEOUT_S", 0.05)

    client = TestClient(main.app)
    r = client.post("/historical", json={"symbol": "ES", "barSize": "1h", "lookback": "1mo"})

    assert r.status_code == 504, r.text
    assert "larger bar size" in r.json()["detail"]
    assert dropped is True  # connection dropped so the stall doesn't leak
