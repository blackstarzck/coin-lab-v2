# FIRST_RUN_GUIDE.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This guide explains what is considered a correct first-run result in a fresh environment and what you must do to see actual PAPER or LIVE strategy execution.

The most important distinction is:

- "the app starts"
- "a strategy session is actually running"

These are not the same thing.

## Expected first-run result
On a fresh boot, the following is normal:

- backend and frontend start successfully
- Dashboard or Monitoring may show `running_session_count=0`
- default strategies and strategy versions are visible
- no PAPER or LIVE strategy session auto-starts on boot
- real execution begins only when a user starts a session from the `Strategies` page or via `POST /api/v1/sessions`

In other words, "default strategies exist" does not mean "default strategies are already running".

## Runtime semantics
- fresh boot does not auto-start trading sessions
- a successful `POST /api/v1/sessions` immediately activates the selected `PAPER` or `LIVE` mode
- the session is expected to become `RUNNING` immediately when runtime startup succeeds
- signals, orders, and positions appear only when live market snapshots satisfy the selected strategy

## Prerequisites
- Python `3.12`
- Node.js `20+`
- npm `10+`
- PowerShell or CMD on Windows
- network access to Upbit public market websocket endpoints

To validate `LIVE` mode, you also need:

- Upbit access key
- Upbit secret key
- `COIN_LAB_LIVE_TRADING_ENABLED=true`
- `COIN_LAB_LIVE_ORDER_NOTIONAL_KRW >= 5000`

## Environment file
The backend reads `backend/.env`.

Minimum local values for realtime PAPER execution:

```env
COIN_LAB_APP_ENV=development
COIN_LAB_LOG_LEVEL=INFO
COIN_LAB_ALLOWED_ORIGINS=["http://localhost:5173"]
COIN_LAB_STORE_BACKEND=memory
COIN_LAB_UPBIT_REST_BASE_URL=https://api.upbit.com
COIN_LAB_UPBIT_WS_PUBLIC_URL=wss://api.upbit.com/websocket/v1
COIN_LAB_UPBIT_WS_PRIVATE_URL=wss://api.upbit.com/websocket/v1/private
```

Additional values required for LIVE execution:

```env
COIN_LAB_UPBIT_ACCESS_KEY=...
COIN_LAB_UPBIT_SECRET_KEY=...
COIN_LAB_LIVE_TRADING_ENABLED=true
COIN_LAB_LIVE_REQUIRE_ORDER_TEST=true
COIN_LAB_LIVE_ORDER_NOTIONAL_KRW=5000
```

Notes:

- Supabase values are not required for the current local runtime path.
- `COIN_LAB_STORE_BACKEND=memory` means session state is not persisted across restarts.
- LIVE must never place orders before an explicit user-started LIVE session exists.

## Install
Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm.cmd ci
```

## Start
Recommended in an IDE terminal:

```powershell
cd C:\path\to\coin-lab
.\start-dev-inline.cmd
```

To open backend and frontend in separate windows:

```powershell
cd C:\path\to\coin-lab
.\start-dev.cmd
```

Manual start:

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm.cmd run dev
```

Health checks:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000/api/v1/health`

## How to see immediate strategy execution
UI flow:

1. Open the `Strategies` page.
2. Select a strategy that has a validated latest version.
3. In the `Launch Session` card, choose `PAPER` or `LIVE`.
4. If using `LIVE`, complete both confirmation switches.
5. Click `Start PAPER now` or `Start LIVE now`.
6. The app should move to Monitoring and show the new session as `RUNNING` immediately.

API flow:

PAPER:

```powershell
Invoke-WebRequest -Method POST http://127.0.0.1:8000/api/v1/sessions -ContentType "application/json" -Body '{
  "mode": "PAPER",
  "strategy_version_id": "stv_001",
  "symbol_scope": {
    "mode": "dynamic",
    "sources": ["top_turnover"],
    "max_symbols": 3,
    "active_symbols": []
  },
  "risk_overrides": {},
  "confirm_live": false,
  "acknowledge_risk": false
}'
```

LIVE:

```powershell
Invoke-WebRequest -Method POST http://127.0.0.1:8000/api/v1/sessions -ContentType "application/json" -Body '{
  "mode": "LIVE",
  "strategy_version_id": "stv_001",
  "symbol_scope": {
    "mode": "dynamic",
    "sources": ["top_turnover"],
    "max_symbols": 3,
    "active_symbols": []
  },
  "risk_overrides": {},
  "confirm_live": true,
  "acknowledge_risk": true
}'
```

## What should happen after session start
Expected result right after a successful start:

- `POST /api/v1/sessions` returns `200` and `status=RUNNING`
- `GET /api/v1/sessions/{sessionId}` returns the same session as `RUNNING`
- Monitoring shows the selected mode badge and a `RUNNING` chip
- signals, orders, and positions begin to appear only when market conditions match the selected strategy

Important:

- `RUNNING` does not guarantee that an order is created immediately
- a strategy can be running while signals/orders/positions remain empty because the market has not matched its rules yet

## Troubleshooting
Dashboard shows a backend load error:

- backend may not have finished starting before frontend loaded
- confirm `http://localhost:8000/api/v1/health` returns `200`
- refresh the browser after backend is healthy

LIVE start is blocked:

- verify `COIN_LAB_LIVE_TRADING_ENABLED`
- verify Upbit access and secret keys exist
- verify `COIN_LAB_LIVE_ORDER_NOTIONAL_KRW >= 5000`
- verify `confirm_live=true` and `acknowledge_risk=true`

Session is `RUNNING` but there are no signals or orders:

- this can be normal
- the runtime only emits execution results when market snapshots satisfy the selected strategy
- inspect active symbols, timeframes, and recent chart data in Monitoring

Sessions disappear after restart:

- this is expected when `COIN_LAB_STORE_BACKEND=memory`
- configure a persistent store if you need cross-restart session history
