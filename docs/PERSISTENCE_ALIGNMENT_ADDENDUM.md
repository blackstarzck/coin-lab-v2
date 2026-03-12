# PERSISTENCE_ALIGNMENT_ADDENDUM.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

References:
- conflict authority: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)
- SQL schema baseline: [DB_SCHEMA_SQL_LEVEL.md](./DB_SCHEMA_SQL_LEVEL.md)
- API payload SSOT: [API_PAYLOADS.md](./API_PAYLOADS.md)

## Purpose
This addendum closes the remaining persistence gaps between the current API/UI contracts and the earlier SQL-level draft.

## Final additions

### strategies
- `labels_json jsonb not null default '[]'::jsonb`
- `latest_version_no integer null`
- `last_7d_return_pct numeric(20,10) null`
- `last_7d_win_rate numeric(20,10) null`

### sessions
- `performance_json jsonb not null default '{}'::jsonb`
- `health_json jsonb not null default '{}'::jsonb`

### signals
- `signal_price numeric(30,10) null`

### positions
- `current_price numeric(30,10) null`
- `unrealized_pnl numeric(30,10) not null default 0`
- `unrealized_pnl_pct numeric(20,10) not null default 0`

### risk_events
- `message text not null default ''`

### backtest_runs
- `created_at timestamptz not null default now()`

### new tables
- `backtest_equity_curve_points`
- `universe_symbols`
- `market_candles`

## Rationale
- `StrategySummary`, monitoring cards, and strategy list payloads already expose labels and 7-day summary metrics directly.
- session detail and monitoring views require materialized health/performance state.
- signal, position, and risk-event APIs already expose `signal_price`, current mark-to-market fields, and human-readable risk messages.
- the monitoring screen requires persistent universe and chart-ready candle data.

## Implementation rule
- repositories must read and write the fields above directly
- workers may update the materialized tables incrementally
- code must not invent additional runtime tables beyond this addendum without another doc update
