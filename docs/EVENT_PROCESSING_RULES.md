# EVENT_PROCESSING_RULES.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document defines the authoritative rules for market event ingestion, normalization, ordering, snapshot creation, and evaluation triggering.

This document is binding for:
- Upbit websocket ingestion worker
- normalization services
- candle builder
- snapshot builder
- strategy evaluation trigger logic
- monitoring data freshness indicators

## Event categories
1. `TRADE_TICK`
2. `ORDERBOOK_SNAPSHOT` (future-ready; not required for MVP)
3. `CANDLE_UPDATE`
4. `CANDLE_CLOSE`
5. `SYSTEM_CONNECTION`
6. `SYSTEM_GAP_RECOVERY`

## Canonical event envelope
Every normalized event must contain:
- `event_id`
- `dedupe_key`
- `symbol`
- `timeframe` (nullable for trade ticks)
- `event_type`
- `event_time`
- `sequence_no` (nullable if unavailable from source)
- `received_at`
- `source`
- `payload`
- `trace_id`

## Ordering rules
### Primary ordering
Processing order for the same symbol is determined by:
1. `event_time`
2. `sequence_no`
3. `received_at`

### Cross-symbol ordering
Cross-symbol strict global ordering is not required. Symbols are processed independently.

### Tie-breaking
If `event_time`, `sequence_no`, and `received_at` are all equal, lower lexical `event_id` wins.

## Deduplication rules
### Dedupe key rules
- `TRADE_TICK`: `{symbol}:{trade_id}` if source trade ID exists; otherwise deterministic hash over source payload fields
- `CANDLE_CLOSE`: `{symbol}:{timeframe}:{candle_start_ts}:close`
- `SYSTEM_CONNECTION`: `{connection_id}:{state}:{timestamp_bucket}`

### Dedupe retention
- tick dedupe cache: minimum 10 minutes
- candle dedupe cache: minimum 48 hours
- system event dedupe cache: minimum 24 hours

### Dedupe behavior
If an incoming event matches a dedupe key already processed:
- drop duplicate event
- do not trigger strategy evaluation
- do emit debug log only if debug logging is enabled

## Buffering and batching
### Trade tick buffering
- ticks may be buffered per symbol for up to 250ms
- batch flush occurs when either:
  - buffer age >= 250ms
  - buffer size >= 200 events
  - a disconnect/reconnect boundary is detected

### Candle update emission
- 1m candle updates may be emitted incrementally for UI only
- strategy evaluation on candles must not run on incremental candle updates unless a strategy explicitly declares `trigger=ON_CANDLE_UPDATE`
- default trigger is `ON_CANDLE_CLOSE`

## Snapshot creation rules
### Snapshot sources
A snapshot may include:
- latest trade price
- current candle state for configured timeframes
- computed indicators
- volume statistics
- symbol status metadata
- risk/session context

### Snapshot freshness thresholds
- tick-driven strategy snapshots: stale after 2 seconds
- 1m strategy snapshots: stale after 70 seconds
- 5m strategy snapshots: stale after 6 minutes
- 15m strategy snapshots: stale after 16 minutes

### Snapshot trigger rules
Create or update a snapshot when:
- a new trade batch flush completes
- a candle closes
- a required indicator recomputation completes
- session/risk state changes in a way that affects execution eligibility

## Strategy evaluation triggers
### Allowed triggers
- `ON_TICK_BATCH`
- `ON_CANDLE_CLOSE`
- `ON_CANDLE_UPDATE`
- `ON_MANUAL_REEVALUATE`

### Default trigger
Strategies default to `ON_CANDLE_CLOSE` unless explicitly configured otherwise.

### Trigger coalescing
If multiple triggering events arrive within the same evaluation window for the same strategy-symbol pair:
- coalesce to one evaluation
- use the newest snapshot
- preserve all source trace IDs in the evaluation log

## Reconnect and gap recovery
### Connection states
- `CONNECTED`
- `DISCONNECTED`
- `RECONNECTING`
- `RECOVERED`
- `DEGRADED`

### Reconnect policy
- backoff sequence: 1s, 2s, 5s, 10s, 20s, 30s max
- jitter required: ±20%
- log every reconnect attempt

### Gap recovery policy
After reconnect:
1. identify last processed event time per symbol
2. fetch recovery data from available REST/candle source where supported
3. rebuild missing candles
4. mark recovered range in system logs
5. if recovery is incomplete, mark symbol state as `DEGRADED`

### Degraded mode
If gap recovery is incomplete:
- monitoring UI must show degraded badge
- strategies requiring affected timeframe data must be skipped until freshness is restored
- skip reason must be logged

## Out-of-order events
If an event arrives older than the latest committed event for the symbol:
- if it is within reorder window (default 2 seconds), reorder and process
- if outside reorder window, discard and log `OUT_OF_ORDER_DROPPED`

## Candle close rules
### Close finalization
A candle is considered closed when the system clock passes the timeframe boundary and the candle close has been committed.

### Late tick handling
Ticks arriving after candle finalization but belonging to the prior interval:
- do not mutate an already committed candle close in MVP mode
- must be logged as `LATE_TICK_AFTER_CLOSE`
- may be incorporated in future replay/rebuild jobs only

## Backpressure rules
If ingest rate exceeds processing rate:
- prioritize preserving `CANDLE_CLOSE` events and connection state events
- tick batches may be dropped only in monitoring-only paths, never in execution-critical paths
- log `BACKPRESSURE_APPLIED`
- raise system warning in monitoring UI if duration > 5 seconds

## Evaluation isolation
- market ingestion must never block on strategy evaluation
- strategy evaluation must occur in separate worker/task context
- storage write latency must not block websocket read loop

## Required logs
Each stage must emit structured logs with `trace_id`:
- raw_receive
- normalize_success / normalize_drop
- buffer_flush
- snapshot_created
- evaluation_started
- evaluation_skipped
- evaluation_completed
- reconnect_attempt
- gap_recovery_started / completed / degraded

## Mandatory invariants
- no duplicate event may produce duplicate strategy execution
- no stale snapshot may be used for execution
- no reconnect event may silently degrade data quality without a visible system log
- candle-close strategies must never evaluate on partial candle close unless explicitly configured
