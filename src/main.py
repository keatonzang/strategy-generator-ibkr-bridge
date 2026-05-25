"""FastAPI bridge: /historical fetches bars via the singleton IB client."""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from ib_insync import ContFuture
from pydantic import BaseModel

from .contracts import UnknownSymbol, resolve_exchange
from .csv_writer import bars_to_csv
from .ibkr_client import get_ib, is_connected
from .mappings import (
    UnknownBarSize,
    UnknownLookback,
    resolve_bar_size,
    resolve_lookback,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)
app = FastAPI(title="IBKR bridge")


BarKey = Literal["1m", "5m", "15m", "1h", "1d"]
LookbackKey = Literal["1mo", "3mo", "6mo", "1y", "2y", "5y"]


class HistoricalRequest(BaseModel):
    symbol: str
    barSize: BarKey
    lookback: LookbackKey


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "ibkrConnected": await is_connected()}


@app.post("/historical")
async def historical(req: HistoricalRequest) -> dict:
    try:
        exchange = resolve_exchange(req.symbol)
    except UnknownSymbol as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        bar_str = resolve_bar_size(req.barSize)
        dur_str = resolve_lookback(req.lookback)
    except (UnknownBarSize, UnknownLookback) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        ib = await get_ib()
    except Exception as exc:
        log.warning("get_ib failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"IBKR Gateway unreachable: {exc}")

    contract = ContFuture(req.symbol.upper(), exchange)
    try:
        await ib.qualifyContractsAsync(contract)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"qualifyContracts failed: {exc}")

    try:
        bars = await asyncio.wait_for(
            ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=dur_str,
                barSizeSetting=bar_str,
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
            ),
            timeout=30,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="IBKR request timed out after 30 s")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"reqHistoricalData failed: {exc}")

    if not bars:
        raise HTTPException(
            status_code=422,
            detail=f"IBKR returned 0 bars for {req.symbol}/{req.barSize}/{req.lookback}",
        )

    return {
        "filename": f"{req.symbol.upper()}-{req.barSize}-{req.lookback}.csv",
        "csv": bars_to_csv(bars),
        "barCount": len(bars),
    }
