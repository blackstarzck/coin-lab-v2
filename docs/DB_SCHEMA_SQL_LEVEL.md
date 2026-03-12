# DB_SCHEMA_SQL_LEVEL.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 실제 SQL migration 수준의 테이블 구조와 제약을 정의한다.  
정식 migration 작성 전, 컬럼 타입·키·인덱스·enum·json shape를 고정하기 위한 문서다.

참조:
- 전략 JSON shape: [STRATEGY_DSL_SPEC.md](./STRATEGY_DSL_SPEC.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

---

## 2. 공통 규칙
- PK는 `text` 기반 application-generated id 사용 (`stg_`, `stv_`, `ses_` 등)
- 시간 컬럼은 `timestamptz`
- 금액/가격/수량은 `numeric(30, 10)` 기본
- 비율/퍼센트는 `numeric(20, 10)`
- `created_at`, `updated_at` audit 컬럼 기본 포함
- 상태 enum은 DB enum 또는 text check constraint 중 하나로 통일
- JSON 컬럼은 `jsonb` 사용
- `deleted_at` soft delete는 현재 전략 핵심 테이블에는 사용하지 않음

---

## 3. enum 목록

### strategy_type
- `dsl`
- `plugin`
- `hybrid`

### session_mode
- `BACKTEST`
- `PAPER`
- `LIVE`

### session_status
- `PENDING`
- `RUNNING`
- `STOPPING`
- `STOPPED`
- `FAILED`

### order_role
- `ENTRY`
- `EXIT`
- `PARTIAL_EXIT`
- `PROTECTIVE_STOP`
- `TAKE_PROFIT`
- `FALLBACK_MARKET`

### order_type
- `MARKET`
- `LIMIT`

### order_state
- `CREATED`
- `SUBMITTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELLED`
- `REJECTED`
- `EXPIRED`
- `FAILED`

### position_state
- `NONE`
- `OPENING`
- `OPEN`
- `CLOSING`
- `CLOSED`
- `FAILED`

### signal_action
- `ENTER`
- `EXIT`
- `SCALE_IN`
- `REDUCE`
- `BLOCK`

### log_level
- `DEBUG`
- `INFO`
- `WARN`
- `ERROR`

---

## 4. strategies

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| strategy_key | text | N |  | unique |
| name | text | N |  |  |
| strategy_type | text | N |  | enum check |
| description | text | Y | null |  |
| is_active | boolean | N | true |  |
| latest_version_id | text | Y | null | FK -> strategy_versions.id |
| created_at | timestamptz | N | now() |  |
| updated_at | timestamptz | N | now() |  |

### constraints
- PK `(id)`
- UNIQUE `(strategy_key)`
- CHECK `strategy_type in ('dsl','plugin','hybrid')`

### indexes
- `idx_strategies_is_active`
- `idx_strategies_updated_at_desc`

---

## 5. strategy_versions

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| strategy_id | text | N |  | FK |
| version_no | integer | N |  | per strategy unique |
| schema_version | text | N |  | DSL schema version |
| config_json | jsonb | N |  | immutable snapshot |
| config_hash | text | N |  | unique per strategy |
| labels | jsonb | N | '[]'::jsonb | string array |
| notes | text | Y | null |  |
| is_validated | boolean | N | false | last validation success |
| validation_summary | jsonb | Y | null | warnings/errors summary |
| created_by | text | Y | null |  |
| created_at | timestamptz | N | now() |  |

### constraints
- PK `(id)`
- FK `(strategy_id) -> strategies(id)` ON DELETE CASCADE
- UNIQUE `(strategy_id, version_no)`
- UNIQUE `(strategy_id, config_hash)`

### json shape
`config_json`은 `STRATEGY_DSL_SPEC.md`를 따른다.

---

## 6. sessions

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| mode | text | N |  | enum |
| status | text | N |  | enum |
| strategy_version_id | text | N |  | 실행 전략 버전 |
| symbol_scope_json | jsonb | N | '{}'::jsonb | active universe config |
| risk_overrides_json | jsonb | N | '{}'::jsonb |  |
| config_snapshot | jsonb | N | '{}'::jsonb | session start 당시 설정 |
| trace_id | text | N |  |  |
| started_at | timestamptz | Y | null |  |
| ended_at | timestamptz | Y | null |  |
| created_at | timestamptz | N | now() |  |
| updated_at | timestamptz | N | now() |  |

### constraints
- FK `(strategy_version_id) -> strategy_versions(id)` ON DELETE RESTRICT
- CHECK mode in (`BACKTEST`,`PAPER`,`LIVE`)
- CHECK status in allowed set

### indexes
- `idx_sessions_mode_status`
- `idx_sessions_started_at_desc`
- `idx_sessions_trace_id`

---

## 7. signals

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| session_id | text | N |  | FK |
| strategy_version_id | text | N |  | FK |
| symbol | text | N |  | e.g. KRW-BTC |
| timeframe | text | N |  | 1m/5m/15m/tick |
| signal_action | text | N |  | enum |
| confidence | numeric(10,6) | Y | null | 0~1 |
| reason_codes | jsonb | N | '[]'::jsonb | string array |
| explain_json | jsonb | Y | null | explain payload |
| blocked | boolean | N | false | risk block 여부 |
| snapshot_time | timestamptz | N |  |  |
| dedupe_key | text | N |  | unique per signal intent |
| created_at | timestamptz | N | now() |  |

### constraints
- FK `(session_id) -> sessions(id)` ON DELETE CASCADE
- FK `(strategy_version_id) -> strategy_versions(id)` ON DELETE RESTRICT
- UNIQUE `(dedupe_key)`

### indexes
- `idx_signals_session_symbol_time`
- `idx_signals_strategy_version_time`

---

## 8. positions

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| session_id | text | N |  | FK |
| strategy_version_id | text | N |  | FK |
| symbol | text | N |  |  |
| position_state | text | N |  | enum |
| side | text | N | 'LONG' | 현물 기준 LONG |
| entry_time | timestamptz | Y | null |  |
| exit_time | timestamptz | Y | null |  |
| avg_entry_price | numeric(30,10) | Y | null |  |
| avg_exit_price | numeric(30,10) | Y | null |  |
| quantity | numeric(30,10) | N | 0 | current qty |
| invested_amount | numeric(30,10) | N | 0 | cumulative cost basis |
| realized_pnl | numeric(30,10) | N | 0 |  |
| realized_pnl_pct | numeric(20,10) | N | 0 |  |
| stop_loss_price | numeric(30,10) | Y | null |  |
| take_profit_price | numeric(30,10) | Y | null |  |
| trailing_stop_price | numeric(30,10) | Y | null |  |
| closed_reason | text | Y | null | enum-like string |
| created_at | timestamptz | N | now() |  |
| updated_at | timestamptz | N | now() |  |

### constraints
- FK `(session_id) -> sessions(id)` ON DELETE CASCADE
- FK `(strategy_version_id) -> strategy_versions(id)` ON DELETE RESTRICT
- CHECK `quantity >= 0`
- UNIQUE partial index 권장: 한 session/strategy/symbol에 대해 `position_state` in OPEN 계열 1개
  - `(session_id, strategy_version_id, symbol)` where `position_state in ('OPENING','OPEN','CLOSING')`

### indexes
- `idx_positions_session_state`
- `idx_positions_symbol_state`

---

## 9. orders

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| position_id | text | Y | null | FK |
| session_id | text | N |  | FK |
| strategy_version_id | text | N |  | FK |
| symbol | text | N |  |  |
| order_role | text | N |  | enum |
| order_type | text | N |  | enum |
| order_state | text | N |  | enum |
| requested_price | numeric(30,10) | Y | null |  |
| executed_price | numeric(30,10) | Y | null | avg fill |
| requested_qty | numeric(30,10) | N |  |  |
| executed_qty | numeric(30,10) | N | 0 |  |
| fee_amount | numeric(30,10) | N | 0 |  |
| slippage_bps | numeric(20,10) | N | 0 |  |
| retry_count | integer | N | 0 |  |
| external_order_id | text | Y | null | LIVE 전용 |
| idempotency_key | text | N |  | unique |
| submitted_at | timestamptz | Y | null |  |
| filled_at | timestamptz | Y | null |  |
| cancelled_at | timestamptz | Y | null |  |
| failure_code | text | Y | null |  |
| created_at | timestamptz | N | now() |  |
| updated_at | timestamptz | N | now() |  |

### constraints
- FK `(position_id) -> positions(id)` ON DELETE SET NULL
- FK `(session_id) -> sessions(id)` ON DELETE CASCADE
- UNIQUE `(idempotency_key)`
- CHECK `requested_qty > 0`
- CHECK `executed_qty >= 0`

### indexes
- `idx_orders_session_symbol_time`
- `idx_orders_state`
- `idx_orders_external_order_id`

---

## 10. backtest_runs

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| strategy_version_id | text | N |  | FK |
| symbols_json | jsonb | N | '[]'::jsonb | symbol list |
| timeframes_json | jsonb | N | '[]'::jsonb | timeframe list |
| date_from | timestamptz | N |  |  |
| date_to | timestamptz | N |  |  |
| initial_capital | numeric(30,10) | N |  |  |
| execution_overrides_json | jsonb | N | '{}'::jsonb |  |
| status | text | N |  | QUEUED/RUNNING/... |
| metrics_json | jsonb | Y | null | summary metrics |
| trace_id | text | N |  |  |
| queued_at | timestamptz | N | now() |  |
| started_at | timestamptz | Y | null |  |
| completed_at | timestamptz | Y | null |  |

### constraints
- FK `(strategy_version_id) -> strategy_versions(id)` ON DELETE RESTRICT
- CHECK `date_from < date_to`

### indexes
- `idx_backtest_runs_strategy_version`
- `idx_backtest_runs_status`
- `idx_backtest_runs_completed_at_desc`

---

## 11. backtest_trades

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| backtest_run_id | text | N |  | FK |
| symbol | text | N |  |  |
| entry_time | timestamptz | N |  |  |
| exit_time | timestamptz | N |  |  |
| entry_price | numeric(30,10) | N |  |  |
| exit_price | numeric(30,10) | N |  |  |
| qty | numeric(30,10) | N |  |  |
| pnl | numeric(30,10) | N |  |  |
| pnl_pct | numeric(20,10) | N |  |  |
| fee_amount | numeric(30,10) | N | 0 |  |
| slippage_amount | numeric(30,10) | N | 0 |  |
| exit_reason | text | N |  |  |

### constraints
- FK `(backtest_run_id) -> backtest_runs(id)` ON DELETE CASCADE

### indexes
- `idx_backtest_trades_run_id`
- `idx_backtest_trades_symbol`

---

## 12. risk_events

| column | type | null | default | note |
|---|---|---:|---|---|
| id | text | N |  | PK |
| session_id | text | N |  | FK |
| strategy_version_id | text | Y | null | FK |
| symbol | text | Y | null |  |
| event_code | text | N |  | e.g. DAILY_LOSS_LIMIT_HIT |
| severity | text | N |  | INFO/WARN/ERROR |
| payload_json | jsonb | N | '{}'::jsonb |  |
| occurred_at | timestamptz | N | now() |  |

### indexes
- `idx_risk_events_session_time`
- `idx_risk_events_code`

---

## 13. system_logs / strategy_execution_logs / order_simulation_logs / risk_control_logs / document_change_logs

### 공통 컬럼
| column | type | null | default | note |
|---|---|---:|---|---|
| id | bigserial | N |  | PK |
| level | text | N |  | DEBUG/INFO/WARN/ERROR |
| trace_id | text | Y | null |  |
| session_id | text | Y | null |  |
| strategy_version_id | text | Y | null |  |
| symbol | text | Y | null |  |
| event_type | text | N |  |  |
| message | text | N |  |  |
| payload_json | jsonb | Y | null |  |
| logged_at | timestamptz | N | now() |  |

### 분리 이유
- 검색 효율
- retention 정책 분리
- UI 탭별 조회 단순화

---

## 14. JSON shape 추가 규칙

### labels
- `jsonb` string array

### strategy_version.validation_summary
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### sessions.symbol_scope_json
```json
{
  "mode": "dynamic",
  "sources": ["top_turnover", "surge"],
  "max_symbols": 10,
  "active_symbols": ["KRW-BTC", "KRW-ETH"]
}
```

### backtest_runs.metrics_json
```json
{
  "total_return_pct": 12.45,
  "max_drawdown_pct": -4.2,
  "win_rate_pct": 57.14,
  "profit_factor": 1.62,
  "trade_count": 28,
  "avg_hold_minutes": 84.3,
  "sharpe_ratio": 1.18
}
```

---

## 15. 삭제 정책
- strategy 삭제 시 strategy_versions는 cascade
- strategy_version은 세션/백테스트 참조가 있으면 물리 삭제 금지 권장
- session 삭제 시 signal/position/order/risk_event/log는 cascade 허용 가능
- backtest_run 삭제 시 backtest_trades cascade

---

## 16. retention 권장
- backtest_trades: 장기 보관
- strategy_execution_logs: 90~180일
- market raw stream: 로컬 고빈도 저장소에서 단기 보관
- document_change_logs: 장기 보관
