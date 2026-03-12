# DB_SCHEMA.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

참조:
- SQL migration 수준 SSOT: [DB_SCHEMA_SQL_LEVEL.md](./DB_SCHEMA_SQL_LEVEL.md)
- 전략 JSON shape: [STRATEGY_DSL_SPEC.md](./STRATEGY_DSL_SPEC.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

## 저장 전략
### Supabase 저장
- strategies
- strategy_versions
- sessions
- signals
- positions
- orders
- backtest_runs
- backtest_trades
- risk_events
- system_logs
- market_ingest_logs
- strategy_execution_logs
- order_simulation_logs
- risk_control_logs
- document_change_logs
- agent_action_logs

### 로컬 저장 권장
- raw trade stream
- raw orderbook stream
- 고빈도 intermediate cache

## 핵심 테이블
### strategies
- id
- strategy_key
- name
- strategy_type
- description
- is_active
- latest_version_id
- created_at
- updated_at

### strategy_versions
- id
- strategy_id
- version_no
- schema_version
- config_json
- config_hash
- labels
- notes
- is_validated
- validation_summary
- created_at
- created_by

### sessions
- id
- mode
- status
- strategy_version_id
- symbol_scope_json
- risk_overrides_json
- config_snapshot
- trace_id
- started_at
- ended_at
- created_at
- updated_at

### signals
- id
- session_id
- strategy_version_id
- symbol
- timeframe
- signal_action
- confidence
- reason_codes
- explain_json
- blocked
- snapshot_time
- dedupe_key

### positions
- id
- session_id
- strategy_version_id
- symbol
- position_state
- side
- entry_time
- exit_time
- avg_entry_price
- avg_exit_price
- quantity
- realized_pnl
- realized_pnl_pct
- stop_loss_price
- take_profit_price
- trailing_stop_price
- closed_reason

### orders
- id
- position_id
- session_id
- strategy_version_id
- symbol
- order_role
- order_type
- order_state
- requested_price
- executed_price
- requested_qty
- executed_qty
- fee_amount
- slippage_bps
- retry_count
- external_order_id
- idempotency_key

### backtest_runs
- id
- strategy_version_id
- symbols_json
- timeframes_json
- date_from
- date_to
- initial_capital
- execution_overrides_json
- status
- metrics_json

### backtest_trades
- id
- backtest_run_id
- symbol
- entry_time
- exit_time
- entry_price
- exit_price
- qty
- pnl
- pnl_pct
- fee_amount
- slippage_amount
- exit_reason

## 권장 인덱스
- unique(strategy_id, version_no)
- unique(signals.dedupe_key)
- unique(orders.idempotency_key)
- index(session_id, symbol, created_at)
- index(strategy_version_id, symbol)
