# TEST_CASES.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document defines the minimum executable test cases that must pass before a feature is considered done. It complements `TEST_STRATEGY.md` and upgrades it into a concrete, implementation-facing spec.

## Scope
This document covers:
- strategy DSL validation tests
- event ingestion and deduplication tests
- backtest execution tests
- paper/live execution guard tests
- monitoring UI state tests
- API contract tests

This document is a mandatory reference for backend, frontend, and worker implementations.

## Rules
- Each test case must have a stable `test_id`.
- Each test case must define `Given / When / Then`.
- Expected outputs must be deterministic unless a tolerance is explicitly declared.
- Test fixtures must be stored under version control.
- A feature is not complete if there is no mapped test case.

## Test data packs

### Fixture packs
- `fixture_market_candles_basic_v1`
  - 1m OHLCV data for 3 symbols
  - no gaps
  - no reconnect cases
- `fixture_market_ticks_dense_v1`
  - dense trade stream for 2 symbols
  - includes duplicated event IDs
  - includes out-of-order arrival
- `fixture_limit_fill_cases_v1`
  - scenarios for fill, no-fill, cancel-replace, fallback-to-market
- `fixture_risk_controls_v1`
  - scenarios for max loss, daily loss cap, duplicate position, emergency stop

### Time rules
- All timestamps use ISO 8601 UTC with millisecond precision.
- Engine-internal event ordering is validated against `event_time` first, then `sequence_no`, then `received_at`.

## Acceptance thresholds
- Monetary amounts: exact unless otherwise specified
- Percentage metrics: tolerance ±0.0001
- Time durations: tolerance ±1 second only where async scheduling is involved
- Backtest trade counts: exact
- Position state transitions: exact

## Section A. Strategy DSL tests

### TC-DSL-001: valid minimal strategy
**Given** a JSON DSL strategy with required top-level fields and one valid entry rule
**When** the strategy validation endpoint is called
**Then** validation must succeed and return `valid=true`

### TC-DSL-002: missing required field
**Given** a JSON DSL strategy without `entry.rules`
**When** validation is called
**Then** the API must return `400` with `error_code=DSL_VALIDATION_FAILED`

### TC-DSL-003: unknown operator rejection
**Given** a strategy using an operator not listed in `STRATEGY_DSL_SPEC.md`
**When** validation is called
**Then** validation must fail and the error payload must include the offending operator path

### TC-DSL-004: explain payload shape
**Given** a valid strategy and a valid snapshot
**When** explain mode is used
**Then** the result must include:
- evaluated operators
- boolean outcomes
- referenced indicators
- final signal decision

### TC-DSL-005: plugin contract compatibility
**Given** a plugin strategy with valid metadata and a valid Python entrypoint
**When** plugin registration is executed
**Then** the system must store the plugin as executable and reject missing required entrypoint methods

## Section B. Event ingestion and sequencing tests

### TC-EVT-001: duplicate event ignored
**Given** two identical trade events with the same dedupe key
**When** ingestion processes both
**Then** only one normalized event must be persisted and only one strategy evaluation trigger may occur

### TC-EVT-002: out-of-order trade arrival
**Given** three trades for the same symbol arriving out of order
**When** ordering rules are applied
**Then** internal processing order must match `event_time + sequence_no`

### TC-EVT-003: reconnect gap recovery
**Given** websocket disconnect and reconnect with a missing interval
**When** gap recovery runs
**Then** the system must mark the interval as recovered or degraded and emit a system log record

### TC-EVT-004: stale snapshot discard
**Given** a snapshot older than freshness threshold
**When** strategy evaluation is requested
**Then** evaluation must be skipped and a stale-snapshot log entry must be created

## Section C. Backtest execution tests

### TC-BT-001: market order entry with fee and slippage
**Given** a valid strategy signal on candle close
**When** a market order is simulated
**Then** entry price must include fee and slippage according to `EXECUTION_SIMULATION_SPEC.md`

### TC-BT-002: limit order filled
**Given** a limit buy below close price and subsequent candle low touches the order price
**When** fill simulation runs
**Then** the order state must transition to `FILLED`

### TC-BT-003: limit order not filled then fallback to market
**Given** a limit buy that remains unfilled for the configured timeout
**When** fallback policy is enabled
**Then** the original order must become `CANCELLED` and a fallback market order must be created and filled

### TC-BT-004: same-candle TP and SL hit
**Given** a position where the same candle reaches both TP and SL
**When** execution priority rules are applied
**Then** the engine must follow the priority specified in `EXECUTION_SIMULATION_SPEC.md`

### TC-BT-005: partial take-profit chain
**Given** a position configured with 3 take-profit levels
**When** price reaches TP1 and TP2 only
**Then** realized PnL and remaining size must be calculated exactly and position must remain open

### TC-BT-006: max concurrent positions cap
**Given** 3 open positions and max concurrent positions set to 3
**When** a 4th valid entry signal appears
**Then** the signal must be rejected with a risk event

## Section D. Paper / Live protection tests

### TC-EXE-001: emergency stop blocks new orders
**Given** a running paper or live session with emergency stop enabled
**When** a new entry signal appears
**Then** no new order may be submitted

### TC-EXE-002: daily loss cap reached
**Given** session realized loss exceeds the configured daily threshold
**When** another entry signal appears
**Then** the engine must reject it and log `DAILY_LOSS_LIMIT_REACHED`

### TC-EXE-003: duplicate position prevention
**Given** a strategy already has an open position for a symbol
**When** another entry signal is emitted for the same strategy-symbol pair
**Then** no second position may be opened

### TC-EXE-004: mode isolation
**Given** a session in `PAPER` mode
**When** execution adapter is selected
**Then** the live order adapter must never be instantiated

## Section E. API contract tests

### TC-API-001: strategy list response shape
**Given** at least one strategy exists
**When** `GET /api/v1/strategies` is called
**Then** response must match the schema defined in `API_PAYLOADS.md`

### TC-API-002: validation error payload shape
**Given** invalid request payload
**When** any write endpoint is called
**Then** response must include `error_code`, `message`, `trace_id`, `timestamp`, and optional `details`

### TC-API-003: pagination consistency
**Given** 30 strategies exist
**When** page 1 and page 2 are requested with the same sort
**Then** result sets must not overlap and total count must remain consistent

### TC-API-004: session create request is single-strategy
**Given** a validated strategy version exists
**When** `POST /api/v1/sessions` is called
**Then** the request/response contract must use a single `strategy_version_id` field and reject array-shaped `strategy_version_ids`

## Section F. Monitoring UI tests

### TC-UI-001: monitoring page loads summary and widgets
**Given** monitoring API returns valid data
**When** `/monitoring` loads
**Then** summary cards, session comparison table, active positions, and signal stream must render

### TC-UI-002: stale/reconnecting badge
**Given** websocket status changes to reconnecting
**When** state updates are emitted
**Then** the UI must show reconnecting status within 1 second

### TC-UI-003: live mode guard dialog
**Given** a user attempts to enable `LIVE`
**When** confirmation dialog is shown
**Then** the required confirmation interaction must be completed before state changes

### TC-UI-004: strategy-json sync
**Given** a user edits a strategy in form mode
**When** the JSON preview is opened
**Then** the JSON must reflect the latest valid form state

## Regression suites
- `suite_smoke_minimum`
  - TC-DSL-001
  - TC-EVT-001
  - TC-BT-001
  - TC-API-001
  - TC-UI-001
- `suite_engine_core`
  - all Section B and Section C cases
- `suite_release_gate`
  - all high-risk test cases: TC-EVT-003, TC-BT-003, TC-BT-004, TC-EXE-001, TC-EXE-002, TC-UI-003

## Required CI gates
- Pull request touching DSL: run all Section A and mapped Section E tests
- Pull request touching execution engine: run Sections B, C, D
- Pull request touching monitoring UI: run Section F and impacted API tests
- Release candidate: run `suite_release_gate`

## Traceability matrix requirement
Every new feature PR must update one of the following:
- add a new test case here
- map existing test cases in the PR description
- explicitly state why no change is required
