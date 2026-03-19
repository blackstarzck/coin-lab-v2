# PROJECT_STRUCTURE.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

References:
- implementation priority: [CODEX_MASTER_PROMPT.md](./CODEX_MASTER_PROMPT.md)
- coding rules: [CODING_GUIDELINES.md](./CODING_GUIDELINES.md)

```text
coin-lab/
|-- docs/
|-- infra/
|   `-- supabase/
|       `-- 001_init.sql
|-- backend/
|   |-- requirements.txt
|   |-- __init__.py
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- router.py
|   |   |   |-- ws_router.py
|   |   |   `-- routes/
|   |   |       |-- __init__.py
|   |   |       |-- backtests.py
|   |   |       |-- health.py
|   |   |       |-- logs.py
|   |   |       |-- monitoring.py
|   |   |       |-- sessions.py
|   |   |       |-- strategies.py
|   |   |       `-- universe.py
|   |   |-- application/
|   |   |   |-- __init__.py
|   |   |   |-- container.py
|   |   |   `-- services/
|   |   |       |-- __init__.py
|   |   |       |-- backtest_service.py
|   |   |       |-- execution_service.py
|   |   |       |-- health_service.py
|   |   |       |-- log_service.py
|   |   |       |-- market_ingest_service.py
|   |   |       |-- monitoring_service.py
|   |   |       |-- runtime_service.py
|   |   |       |-- session_service.py
|   |   |       |-- stream_service.py
|   |   |       |-- strategy_service.py
|   |   |       |-- strategy_validator.py
|   |   |       `-- universe_service.py
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py
|   |   |   |-- error_codes.py
|   |   |   |-- exceptions.py
|   |   |   |-- logging.py
|   |   |   `-- trace.py
|   |   |-- domain/
|   |   |   |-- __init__.py
|   |   |   |-- entities/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- session.py
|   |   |   |   `-- strategy.py
|   |   |   `-- value_objects/
|   |   |       |-- __init__.py
|   |   |       `-- pagination.py
|   |   |-- infrastructure/
|   |   |   |-- __init__.py
|   |   |   |-- db/
|   |   |   |   `-- __init__.py
|   |   |   |-- logging/
|   |   |   |   `-- __init__.py
|   |   |   |-- repositories/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- in_memory_lab_store.py
|   |   |   |   |-- lab_store.py
|   |   |   |   `-- postgres_lab_store.py
|   |   |   `-- upbit/
|   |   |       |-- __init__.py
|   |   |       `-- websocket_adapter.py
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- backtest.py
|   |   |   |-- common.py
|   |   |   |-- execution.py
|   |   |   |-- log.py
|   |   |   |-- market.py
|   |   |   |-- monitoring.py
|   |   |   |-- runtime.py
|   |   |   |-- session.py
|   |   |   |-- strategy.py
|   |   |   |-- stream.py
|   |   |   `-- universe.py
|   |   `-- workers/
|   |       |-- __init__.py
|   |       `-- market_ingest.py
|   `-- tests/
|       |-- __init__.py
|       |-- test_api_contracts.py
|       |-- test_execution_service.py
|       |-- test_market_ingest_service.py
|       |-- test_runtime_service.py
|       `-- test_upbit_websocket_adapter.py
|-- frontend/
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- tsconfig.json
|   |-- vite.config.ts
|   `-- src/
|       |-- main.tsx
|       |-- vite-env.d.ts
|       |-- app/
|       |   |-- App.tsx
|       |   `-- providers.tsx
|       |-- entities/
|       |   |-- backtest/
|       |   |   `-- types.ts
|       |   |-- market/
|       |   |   `-- types.ts
|       |   |-- log/
|       |   |   `-- types.ts
|       |   |-- session/
|       |   |   `-- types.ts
|       |   `-- strategy/
|       |       `-- types.ts
|       |-- features/
|       |   |-- backtests/
|       |   |   `-- api.ts
|       |   |-- logs/
|       |   |   `-- api.ts
|       |   |-- monitoring/
|       |   |   |-- api.ts
|       |   |   `-- useChartStream.ts
|       |   |-- sessions/
|       |   |   `-- api.ts
|       |   `-- strategies/
|       |       `-- api.ts
|       |-- pages/
|       |   |-- BacktestsPage.tsx
|       |   |-- ComparePage.tsx
|       |   |-- DashboardPage.tsx
|       |   |-- LogsPage.tsx
|       |   |-- MonitoringPage.tsx
|       |   |-- SettingsPage.tsx
|       |   `-- StrategiesPage.tsx
|       |-- shared/
|       |   |-- api/
|       |   |   `-- client.ts
|       |   |-- charts/
|       |   |   |-- CandlestickChart.tsx
|       |   |   `-- LineChart.tsx
|       |   |-- config/
|       |   |   `-- env.ts
|       |   |-- lib/
|       |   |   `-- format.ts
|       |   |-- query/
|       |   |   `-- client.ts
|       |   `-- types/
|       |       `-- api.ts
|       |-- stores/
|       |   `-- ui-store.ts
|       |-- theme/
|       |   `-- theme.ts
|       `-- widgets/
|           `-- layout/
|               `-- AppShell.tsx
|-- workers/
|   |-- backtest.py
|   |-- market_ingest.py
|   `-- strategy_runtime.py
`-- .gitignore
```

## Notes
- `backend/app/domain/strategy_runtime/` now holds the staged domain objects for the layered execution upgrade, including shared market structures, strategy setups, execution plans, and explain snapshots.
- `backend/app/application/strategy_runtime/detectors/` now hosts extracted detector modules for trend context, order block, fair value gap, structure break, and retest, plus shared candle-resolution helpers used by `smc_confluence_v1`.
- `backend/app/application/strategy_runtime/composers/`, `.../explain/`, and `.../mappers/` now provide the composer-based decision layer, explain payload assembly, and draft-to-plugin/hybrid mapping used by both plugin wrappers and hybrid strategies.
- `backend/app/application/strategy_runtime/execution/` now isolates sizing, entry intent, order lifecycle, and exit-trigger policies so `ExecutionService` can orchestrate reusable execution modules instead of owning every rule inline.
- `backend/tests/strategy_runtime/` now pins the domain-object contracts with serialization and explain-payload focused tests before detector/composer/policy migration starts.
- `backend/tests/strategy_runtime/composers/` now locks the hybrid runtime and composer mapping behavior so plugin and hybrid strategies share the same deterministic decision path.
- `backend/tests/strategy_runtime/detectors/` now locks detector contracts for trend context, order block, fair value gap, structure break, and retest before composer migration begins.
- `backend/app/application/services` now contains strategy, session, monitoring, backtest, log, universe, and stream orchestration over the shared repository contract.
- `backend/app/application/services/signal_generator.py` now supports `dsl`, `plugin`, and `hybrid` strategy types, while `strategy_validator.py` validates registered composers and execution-module config for hybrid definitions.
- `backend/app/infrastructure/repositories/lab_store.py` defines the shared repository contract, and `postgres_lab_store.py` enables optional Supabase/Postgres-backed persistence through `COIN_LAB_STORE_BACKEND=postgres`.
- `backend/app/api/ws_router.py`, `backend/app/application/services/stream_service.py`, and `backend/app/api/routes/universe.py` add websocket monitoring/chart streams plus universe read APIs.
- `backend/app/workers/market_ingest.py` now persists chart-ready candle snapshots into the active store, and `workers/strategy_runtime.py` persists accepted or rejected runtime outcomes through the same repository contract.
- `backend/tests/test_api_contracts.py` covers session subresources, backtest run/compare flow, log filtering, and LIVE confirmation safety.
- `backend/app/application/services/market_ingest_service.py` adds normalized event handling, tick buffering, dedupe, reorder-window drops, reconnect delay helpers, and snapshot freshness checks.
- `backend/app/infrastructure/upbit/websocket_adapter.py` builds official Upbit websocket subscription payloads and normalizes public trade, orderbook, candle, and connection messages into the internal event envelope.
- `backend/app/infrastructure/upbit/live_execution_adapter.py` adds the guarded REST execution boundary for LIVE mode, including HS512 auth, deterministic identifiers, optional order-test checks, and recovery by exchange identifier lookup.
- `backend/app/application/services/execution_service.py` now delegates sizing, entry intent planning, fill simulation, and exit trigger evaluation to the strategy-runtime execution policy modules while preserving the current BACKTEST/PAPER session flow.
- `backend/app/application/services/backtest_service.py` can now replay deterministic `snapshot_series` inputs through the shared execution stack, persist closed trades in bulk, and derive metrics/equity curves from actual replay output.
- `backend/app/application/services/execution_adapters.py` keeps simulated mode adapters lightweight while leaving the LIVE exchange adapter isolated in infra.
- `backend/app/application/services/runtime_service.py` ties stale-snapshot checks, risk guards, execution-adapter selection, and order submission into one signal-processing step.
- `workers/backtest.py` and `workers/strategy_runtime.py` are no longer placeholders; they now expose simple CLI entry points for replaying backtests from JSON payloads and manually reevaluating running sessions.
- `backend/tests/test_market_ingest_service.py` locks the ingest invariants around duplicate drops, out-of-order rejection, tick flushes, freshness thresholds, and reconnect backoff.
- `backend/tests/test_execution_service.py`, `backend/tests/test_runtime_service.py`, `backend/tests/test_live_execution_adapter.py`, and `backend/tests/test_upbit_websocket_adapter.py` cover execution simulation basics, runtime routing, live-order guard behavior, and adapter normalization contracts.
- `backend/tests/test_postgres_store_smoke.py` provides an env-gated persistence smoke path for real Postgres or Supabase-backed environments.
- The frontend shell now exposes dashboard, monitoring, strategies, backtests, compare, logs, and settings pages from a shared Zustand UI store.
- `frontend/src/app/App.tsx` now lazy-loads heavy pages, and `frontend/vite.config.ts` splits charts, MUI, query, and React vendor chunks.
- `frontend/src/shared/charts` isolates the lightweight-charts adapter away from page logic, and `frontend/src/features/monitoring/useChartStream.ts` handles chart websocket streaming with reconnect.
- `shared/lib/format.ts` centralizes KRW, percentage, and timestamp formatting across the UI.
