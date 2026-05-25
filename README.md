# strategy-generator-ibkr-bridge

FastAPI sidecar that exposes Interactive Brokers historical-data fetches as
JSON for the [strategy-generator](https://github.com/keatonzang/strategy-generator)
webapp.

Runs alongside an IB Gateway container in `docker compose` on the deploy VM.

## Design

- High-level deploy shape: `strategy-generator/docs/superpowers/specs/2026-05-25-ibkr-deployed-integration-design.md`
- Sidecar internals, API contract, error mapping: `strategy-generator/docs/superpowers/specs/2026-05-10-ibkr-data-integration-design.md`

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pytest-asyncio
pytest
# To run against a real Gateway on the laptop:
IBKR_HOST=127.0.0.1 uvicorn src.main:app --port 5050
```

## Endpoints

- `GET /health` → `{ok: bool, ibkrConnected: bool}`
- `POST /historical` body `{symbol, barSize, lookback}` → `{filename, csv, barCount}`
