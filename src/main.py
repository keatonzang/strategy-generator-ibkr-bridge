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
from .ibkr_client import drop_connection, get_ib, is_connected
from .mappings import (
    UnknownBarSize,
    UnknownLookback,
    UnsupportedCombo,
    resolve_bar_size,
    resolve_lookback,
    validate_combo,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)
app = FastAPI(title="IBKR bridge")


BarKey = Literal["1m", "5m", "15m", "1h", "1d"]
LookbackKey = Literal["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# Max seconds to wait for IBKR to return bars before giving up. IBKR stalls
# silently on over-limit requests, so this must fire to avoid hanging forever.
HISTORICAL_TIMEOUT_S = 30


class HistoricalRequest(BaseModel):
    symbol: str
    barSize: BarKey
    lookback: LookbackKey


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "ibkrConnected": await is_connected()}


@app.post("/historical")
async def historical(req: HistoricalRequest) -> dict:
    log.info(
        "historical request symbol=%s bar=%s lookback=%s",
        req.symbol, req.barSize, req.lookback,
    )

    try:
        exchange = resolve_exchange(req.symbol)
    except UnknownSymbol as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        bar_str = resolve_bar_size(req.barSize)
        dur_str = resolve_lookback(req.lookback)
    except (UnknownBarSize, UnknownLookback) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Reject over-volume combos up front: IBKR would stall silently for 30 s.
    try:
        validate_combo(req.barSize, req.lookback)
    except UnsupportedCombo as exc:
        log.info("historical rejected (over limit): %s", exc)
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
            timeout=HISTORICAL_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        # The request is still open on IB Gateway; drop the client so it doesn't
        # leak and stall every later request (see ibkr_client.drop_connection).
        log.warning(
            "historical timed out symbol=%s bar=%s lookback=%s; dropping IB connection",
            req.symbol, req.barSize, req.lookback,
        )
        await drop_connection()
        raise HTTPException(
            status_code=504,
            detail=(
                f"No data returned for {req.symbol.upper()} "
                f"{req.barSize}/{req.lookback} within {HISTORICAL_TIMEOUT_S}s. "
                f"Try a larger bar size or a shorter lookback."
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"reqHistoricalData failed: {exc}")

    log.info(
        "historical ok symbol=%s bar=%s lookback=%s bars=%d",
        req.symbol, req.barSize, req.lookback, len(bars),
    )

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
