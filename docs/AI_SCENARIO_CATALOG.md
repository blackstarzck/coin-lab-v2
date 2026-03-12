# AI_SCENARIO_CATALOG.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: AI 유지보수 시나리오와 기대 결과를 변경 유형별로 표준화한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document defines reusable scenario packs and expected-result rules for AI-assisted maintenance work.

Use it with `AI_MAINTENANCE_WORKFLOW.md`. The workflow explains when and how to generate scenarios. This document explains what those scenarios should assert and what a good expected result looks like.

## Core rule
Every generated scenario must include an explicit `expected_result` before validation starts.

`expected_result` must be:
- observable
- deterministic where possible
- specific about what must happen
- specific about what must not happen
- tied to the governing docs and mapped test IDs

Bad:
- feature works correctly
- no issue
- UI looks fine

Good:
- response returns `400` with `error_code=DSL_VALIDATION_FAILED` and includes the invalid field path
- order remains `CANCELLED`, exactly one fallback market order is created, and the rejection plus fallback logs share the same `trace_id`
- reconnect badge appears within 1 second and the stale-summary badge disappears after the first fresh snapshot

## Expected-result writing guide
For each scenario, write the expected result across the relevant dimensions:

1. Contract surface
   - status code, payload shape, enum, field names, serialization rules
2. State surface
   - created, updated, deleted, or unchanged entities and exact state transitions
3. Persistence surface
   - what is written, not written, migrated, replayed, or rejected
4. Log and telemetry surface
   - required log channel, error code, trace propagation, degraded markers
5. UI surface
   - rendered state, badge, dialog, empty/error handling, timing expectations
6. Safety surface
   - blocked actions, confirmation requirements, unchanged money-impacting state
7. Performance surface
   - invariant preservation under burst, replay, load, or repeated execution

If a dimension is not relevant, omit it explicitly in the scenario card instead of leaving it ambiguous.

## Mandatory expectation fields by scenario type

| Scenario type | Expected result must include |
| --- | --- |
| `CONTRACT` | exact field names, enum values, status code, compatibility or explicit rejection rule |
| `NOMINAL_FLOW` | successful output, downstream side effects, user-visible result |
| `BOUNDARY_VALIDATION` | exact rejection condition, documented error payload, unchanged protected state |
| `STATE_TRANSITION` | from-state, to-state, forbidden alternatives, side effects on related entities |
| `TEMPORAL_ORDERING` | ordering basis, dedupe rule, freshness rule, timeout or priority outcome |
| `FAILURE_RECOVERY` | failure trigger, fallback or retry path, duplicate prevention, degraded-state observability |
| `SAFETY_GUARD` | blocked action, guard reason, unchanged execution state, required logs or dialogs |
| `SYNC_CONSISTENCY` | two or more layers showing the same canonical value, no stale divergence |
| `PERSISTENCE_COMPATIBILITY` | migration behavior, old-data handling, replay result, explicit backward-compatibility stance |
| `REGRESSION_PERFORMANCE` | previously broken behavior no longer reproduces, key invariants preserved under repeated or burst execution |

## Scenario card extension
Use the base scenario card from `AI_MAINTENANCE_WORKFLOW.md` and extend `expected_result` with the following structure when useful:

```md
- expected_result:
  - must_happen:
    - ...
  - must_not_happen:
    - ...
  - state_assertions:
    - ...
  - contract_assertions:
    - ...
  - log_assertions:
    - ...
  - ui_assertions:
    - ...
  - tolerance:
    - exact | percentage | time
```

## Category scenario packs

### 1. Strategy DSL change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-DSL-CON-001` | `CONTRACT` | `TC-DSL-001` | A valid minimal strategy is accepted, `valid=true` is returned, and no undocumented canonicalization changes the stored shape. | validator unit test plus API contract assertion |
| `SCN-DSL-BND-001` | `BOUNDARY_VALIDATION` | `TC-DSL-002` | Missing required structure returns `400`, `error_code=DSL_VALIDATION_FAILED`, and the invalid path is included in details. No strategy version is persisted. | API test plus persistence assertion |
| `SCN-DSL-BND-002` | `BOUNDARY_VALIDATION` | `TC-DSL-003` | Unknown operators are rejected explicitly. The response identifies the offending operator path and does not silently coerce to another operator. | validator unit test |
| `SCN-DSL-SYNC-001` | `SYNC_CONSISTENCY` | `TC-UI-004` | Form state, JSON preview, backend validator input, and stored payload all match the same canonical structure after save. | frontend integration test plus API roundtrip |
| `SCN-DSL-REG-001` | `REGRESSION_PERFORMANCE` | `suite_smoke_minimum` | Previously valid strategies remain valid unless the spec explicitly changed. If compatibility is intentionally broken, the rejection is explicit and documented. | fixture replay against old strategy samples |

### 2. Execution / fill logic change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-EXE-NOM-001` | `NOMINAL_FLOW` | `TC-BT-001` | Market entry applies fee and slippage exactly as documented. Entry price, cost basis, and resulting position size are deterministic. | execution unit test |
| `SCN-EXE-STATE-001` | `STATE_TRANSITION` | `TC-BT-002` | Order and position states move through the documented lifecycle only. No skipped or duplicate state transitions occur. | state-transition test with persisted entities |
| `SCN-EXE-TIME-001` | `TEMPORAL_ORDERING` | `TC-BT-004` | Same-candle TP and SL conflicts resolve by the documented priority, and only one exit path is applied. | candle-conflict simulation test |
| `SCN-EXE-FAIL-001` | `FAILURE_RECOVERY` | `TC-BT-003` | Timed-out limit orders become `CANCELLED`, exactly one fallback market order is created when enabled, and no double fill occurs. | execution simulation test plus log assertion |
| `SCN-EXE-SAFE-001` | `SAFETY_GUARD` | `TC-EXE-001`, `TC-EXE-002` | Emergency stop or daily loss cap blocks new orders, preserves the pre-existing position state, and emits the documented rejection reason. | runtime test plus risk-log assertion |
| `SCN-EXE-REG-001` | `REGRESSION_PERFORMANCE` | `suite_release_gate` | Critical metrics and trade invariants do not regress outside documented tolerances after the logic change. | replay test against golden fixtures |

### 3. Event processing change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-EVT-NOM-001` | `NOMINAL_FLOW` | `TC-EVT-001` | The first valid event is processed, duplicates are ignored, and only one downstream evaluation trigger fires. | ingest service test |
| `SCN-EVT-TIME-001` | `TEMPORAL_ORDERING` | `TC-EVT-002` | Internal processing order follows `event_time`, then `sequence_no`, then `received_at`. Out-of-order arrival does not corrupt snapshots. | ordering test with synthetic timestamps |
| `SCN-EVT-BND-001` | `BOUNDARY_VALIDATION` | `TC-EVT-004` | Stale snapshots are explicitly skipped, no evaluation runs, and a stale-snapshot log entry is emitted. | freshness threshold test |
| `SCN-EVT-FAIL-001` | `FAILURE_RECOVERY` | `TC-EVT-003` | Reconnect gap recovery marks the interval as `recovered` or `degraded`, creates the documented log record, and does not silently claim full health. | reconnect simulation plus log assertion |
| `SCN-EVT-REG-001` | `REGRESSION_PERFORMANCE` | `suite_release_gate` | Under burst traffic, dedupe, ordering, and freshness invariants still hold without duplicate downstream actions. | burst replay test |

### 4. DB schema change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-DB-CON-001` | `CONTRACT` | mapped from impacted API tests | API payloads and stored row shapes both reflect the new schema exactly. No undocumented nullable or enum changes leak into the contract. | migration plus API smoke test |
| `SCN-DB-PERS-001` | `PERSISTENCE_COMPATIBILITY` | mapped from impacted fixtures | Existing rows or snapshots either migrate successfully or fail explicitly with a documented compatibility rule. Silent truncation is not allowed. | migration test against pre-change fixtures |
| `SCN-DB-BND-001` | `BOUNDARY_VALIDATION` | mapped from impacted write paths | Invalid rows are rejected with deterministic validation or database errors, and partial writes do not leave broken dependent records. | repository integration test |
| `SCN-DB-REG-001` | `REGRESSION_PERFORMANCE` | mapped from impacted runtime suites | Reprocessing the same historical fixtures yields consistent state and does not create duplicate derived records. | replay test against migrated store |

### 5. API contract change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-API-CON-001` | `CONTRACT` | `TC-API-001` | Response matches the updated spec exactly, including field names, optionality, enums, and timestamps. | API contract test |
| `SCN-API-BND-001` | `BOUNDARY_VALIDATION` | `TC-API-002` | Invalid requests return the standard error envelope with `error_code`, `message`, `trace_id`, `timestamp`, and `details` when relevant. | endpoint validation test |
| `SCN-API-SYNC-001` | `SYNC_CONSISTENCY` | mapped from frontend type checks | Frontend types, API schemas, and server responses agree on the same shape. No client-only field assumptions remain. | typecheck plus API fixture roundtrip |
| `SCN-API-REG-001` | `REGRESSION_PERFORMANCE` | `TC-API-003`, `TC-API-004` | Existing pagination, session shape, and list invariants remain correct unless intentionally changed and documented. | API regression suite |

### 6. Monitoring UI change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-UI-NOM-001` | `NOMINAL_FLOW` | `TC-UI-001` | Monitoring page renders summary cards, compare table, active positions, and signal stream when valid data is returned. | frontend integration test |
| `SCN-UI-BND-001` | `BOUNDARY_VALIDATION` | mapped from loading and error states | Loading, empty, stale, and error states are distinct, recoverable, and do not render misleading healthy data. | UI state test |
| `SCN-UI-SYNC-001` | `SYNC_CONSISTENCY` | mapped from monitoring detail flows | Summary values and detail views show the same session state after a refresh or websocket update. | UI integration plus mock stream |
| `SCN-UI-SAFE-001` | `SAFETY_GUARD` | `TC-UI-003` | `LIVE`-related actions require the documented confirmation flow before state changes. Unsafe transitions do not proceed from a single click. | dialog integration test |
| `SCN-UI-REG-001` | `REGRESSION_PERFORMANCE` | mapped from impacted UI suites | Realtime updates do not break layout, duplicate rows, or hide warning badges under repeated refreshes. | repeated-stream UI test |

### 7. UI visual / design system change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-DS-NOM-001` | `NOMINAL_FLOW` | mapped from impacted screen smoke tests | Updated tokens and shared components render the intended screen family with the documented hierarchy, spacing, and semantic emphasis. No placeholder styling or fallback component slips through. | visual smoke test plus component story review |
| `SCN-DS-BND-001` | `BOUNDARY_VALIDATION` | mapped from responsive and state surfaces | Loading, empty, disabled, dense-table, and narrow-width states remain readable after the visual change. Accent, glow, and semantic colors do not overpower the core data. | responsive UI state test |
| `SCN-DS-SYNC-001` | `SYNC_CONSISTENCY` | mapped from shared component usage | The same status, button, card, and table patterns render consistently across Dashboard, Monitoring, Strategies, and Settings where the role is the same. | cross-screen snapshot review |
| `SCN-DS-SAFE-001` | `SAFETY_GUARD` | `TC-UI-003` when applicable | If the visual change affects `LIVE` warnings, kill actions, or dangerous confirmations, those cues remain more prominent than neutral or success affordances and cannot be mistaken for ordinary actions. | dialog/banner emphasis review plus integration test |
| `SCN-DS-REG-001` | `REGRESSION_PERFORMANCE` | mapped from impacted UI suites | The redesign does not reintroduce clipped text, hidden warnings, unreadable dense tables, or broken dark-theme contrast on previously working screens. | regression screenshot suite |

### 8. Coding convention / architecture change

| Scenario ID | Type | Maps to | Expected result | Default verification |
| --- | --- | --- | --- | --- |
| `SCN-ARC-NOM-001` | `NOMINAL_FLOW` | mapped from impacted feature suite | The refactored boundary preserves observable product behavior while moving logic to the documented layer. | focused regression suite |
| `SCN-ARC-FAIL-001` | `FAILURE_RECOVERY` | mapped from runtime paths | Retry, reconnect, cancellation, or fallback behavior remains intact after the boundary move. | runtime integration test |
| `SCN-ARC-REG-001` | `REGRESSION_PERFORMANCE` | mapped from impacted release-gate suite | The refactor does not reintroduce prior bugs or materially worsen the critical path. | release-gate subset |

## Escalation rules by expected-result failure

| Failure pattern | Default action |
| --- | --- |
| Expected result is vague or unobservable | Rewrite the scenario before running it |
| Product behavior and doc behavior diverge | Follow SSOT priority and patch docs or code before continuing |
| Safe path and risky path are both plausible | Ask the user |
| Only logs fail but user-visible state is correct | Treat as a real failure if logs are part of the documented behavior |
| Test passes but expected result omitted a critical negative assertion | Expand the expected result and rerun |
| Old data works only through silent coercion | Treat as `SPEC_GAP` or compatibility defect, not a pass |

## Practical default
If time is limited, do not reduce the number of scenario types. Reduce breadth inside each type, but still keep:
- one high-confidence nominal path
- one failure or boundary path
- one safety or temporal path when relevant
- one regression path for the changed behavior
