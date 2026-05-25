"""Singleton ib_insync.IB wrapper with lazy connect.

Why singleton: ib_insync holds a persistent event loop and TCP socket;
recreating per request would add ~3–5 s to every call.

Why lazy: FastAPI must not block startup on IBKR — IB Gateway can take
30–60 s to finish IBC autologin. /health returns ibkrConnected=False
until the first successful connect.
"""

from __future__ import annotations

import asyncio
import logging
import os

from ib_insync import IB

log = logging.getLogger(__name__)

_ib: IB | None = None
_lock = asyncio.Lock()


def _config() -> dict:
    return {
        "host": os.environ.get("IBKR_HOST", "ib-gateway"),
        "port": int(os.environ.get("IBKR_PORT", "4002")),
        "clientId": int(os.environ.get("IBKR_CLIENT_ID", "42")),
        "readonly": True,  # mute order/account-query Error 321 on connect
    }


async def get_ib() -> IB:
    """Return a connected IB instance. Connects (or reconnects) on demand."""
    global _ib
    async with _lock:
        if _ib is None:
            _ib = IB()
        if not _ib.isConnected():
            cfg = _config()
            log.info("Connecting to IBKR at %s:%s clientId=%s", cfg["host"], cfg["port"], cfg["clientId"])
            await _ib.connectAsync(**cfg)
    return _ib


async def is_connected() -> bool:
    return _ib is not None and _ib.isConnected()


async def reset_for_tests() -> None:
    """Drop the singleton so tests can re-monkeypatch get_ib."""
    global _ib
    if _ib is not None and _ib.isConnected():
        _ib.disconnect()
    _ib = None
