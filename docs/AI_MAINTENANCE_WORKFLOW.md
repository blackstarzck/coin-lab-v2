# AI_MAINTENANCE_WORKFLOW.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document defines the mandatory workflow an AI agent must follow when performing maintenance or behavior-changing work.

It complements `DOC_UPDATE_CHECKLIST.md`, `TEST_CASES.md`, and `AI_SCENARIO_CATALOG.md` by defining how scenarios are generated, classified, validated, and turned into implementation decisions.

## When this workflow is required
Use this workflow when a task changes or may change:
- strategy DSL or validation behavior
- execution or fill logic
- event processing or realtime ordering behavior
- DB schema or stored JSON shape
- API contracts
- monitoring UI behavior
- shared UI visual behavior or design system rules
- state transitions
- logging, error handling, or risk controls that affect observable behavior

## Core rules
- Do not finalize behavior-changing code without generating scenarios first.
- Every scenario must be linked to source-of-truth documents and mapped test cases, or explicitly note the gap.
- A passing nominal path is not enough. Boundary, failure, or safety scenarios must exist when the change type requires them.
- Validate required scenarios one by one. Do not treat a partially executed set as full confidence.
- If validation exposes a spec gap, update the relevant docs first.
- If validation exposes multiple plausible product behaviors, ask the user instead of silently choosing one.

## Workflow

### 1. Classify the change
- Select the primary change category from `DOC_UPDATE_CHECKLIST.md`.
- Mark impacted modes: `BACKTEST`, `PAPER`, `LIVE`.
- List the relevant SSOT docs.
- Map existing `TEST_CASES.md` IDs or record that new test coverage is required.

### 2. Generate the scenario inventory
- Produce the scenario list before finalizing code.
- Include at least one scenario for each required scenario type in this document.
- Add one regression scenario for every bug fix.
- Add one negative or boundary scenario for every new validation branch.
- Add one ordering or idempotency scenario for any async, streaming, or realtime path.
- Add one compatibility scenario for any schema, API, or persistence change.
- Write the expected result before running the scenario. Use `AI_SCENARIO_CATALOG.md` for expected-result patterns and category packs.

### 3. Classify each scenario
Each scenario must define:
- `scenario_id`
- `change_category`
- `scenario_type`
- `risk_tags`
- `modes`
- `source_docs`
- `mapped_test_ids`
- `preconditions`
- `action`
- `expected_result`
- `verification_method`

`expected_result` must include:
- what must happen
- what must not happen
- the observable surface to inspect such as API payload, persisted state, log channel, or UI output

### 4. Prioritize execution
Run scenario types in this order:
1. `CONTRACT`
2. `NOMINAL_FLOW`
3. `BOUNDARY_VALIDATION`
4. `STATE_TRANSITION`
5. `TEMPORAL_ORDERING`
6. `FAILURE_RECOVERY`
7. `SAFETY_GUARD`
8. `SYNC_CONSISTENCY`
9. `PERSISTENCE_COMPATIBILITY`
10. `REGRESSION_PERFORMANCE`

Run high-risk scenarios first inside each type:
- `MONEY_IMPACT`
- `LIVE_SAFETY`
- `DATA_LOSS`
- `STATE_CORRUPTION`
- `USER_VISIBLE_BREAK`
- `BACKWARD_COMPATIBILITY`

### 5. Validate one by one
For each scenario:
- run or simulate the verification method
- record `PASS`, `PARTIAL_PASS`, `FAIL`, or `BLOCKED`
- capture the observed result and exact mismatch
- classify the root cause immediately

### 6. Classify the outcome
Use one of:
- `SPEC_GAP`
- `IMPLEMENTATION_DEFECT`
- `TEST_OR_FIXTURE_DEFECT`
- `ENVIRONMENT_BLOCKER`
- `LEGACY_BEHAVIOR_MISMATCH`

### 7. Decide the next action
- `PASS`: if all required scenario types pass, update code, docs, and changelog in the same work unit.
- `PARTIAL_PASS`: proceed without asking the user only when failed scenarios are low-risk, unrelated to changed behavior, and the delivered scope can be safely narrowed. Otherwise stop and ask.
- `FAIL` with `IMPLEMENTATION_DEFECT`: fix the code and rerun affected scenarios.
- `FAIL` with `SPEC_GAP`: update the relevant doc first. Ask the user if more than one product behavior is plausible.
- `FAIL` with `TEST_OR_FIXTURE_DEFECT`: fix the fixture or test harness, then rerun. Do not claim product behavior is correct until rerun passes.
- `BLOCKED` with `ENVIRONMENT_BLOCKER`: do not claim completion. Report what could not be verified.
- `LEGACY_BEHAVIOR_MISMATCH`: compare code against SSOT docs. If docs are wrong, patch docs first. If code is wrong, patch code.

## Scenario type taxonomy

### 1. `CONTRACT`
Use for request and response schemas, stored JSON shape, enums, frontend/backend type alignment, and event envelope shape.

Typical checks:
- field presence and names
- type and enum alignment
- explicit compatibility or rejection of old shapes

### 2. `NOMINAL_FLOW`
Use for the intended successful path.

Typical checks:
- main feature works end to end
- expected payload, state, or rendering appears

### 3. `BOUNDARY_VALIDATION`
Use for missing fields, invalid enums, min/max limits, tolerance edges, empty states, and null handling.

Typical checks:
- documented validation error
- deterministic rejection reason

### 4. `STATE_TRANSITION`
Use when statuses, lifecycles, or phase changes are affected.

Typical checks:
- allowed transitions
- forbidden transitions
- required side effects on transition

### 5. `TEMPORAL_ORDERING`
Use for async, streaming, reconnect, stale data, timeout, reorder windows, or same-candle conflicts.

Typical checks:
- duplicate suppression
- processing order
- freshness rules
- timeout or priority resolution

### 6. `FAILURE_RECOVERY`
Use for retry, fallback, degraded mode, partial success, and resume after interruption.

Typical checks:
- fallback path is explicit
- retry does not duplicate work
- degraded state is observable

### 7. `SAFETY_GUARD`
Use for `LIVE` or `PAPER` protection, risk caps, emergency stop, destructive operations, or money-impacting changes.

Typical checks:
- unsafe action is blocked
- confirmation or guard step is enforced
- rejection reason is logged

### 8. `SYNC_CONSISTENCY`
Use when two views or layers must stay aligned.

Typical checks:
- form to JSON sync
- backend schema to frontend type sync
- summary widget to detail page consistency

### 9. `PERSISTENCE_COMPATIBILITY`
Use for DB schema changes, migrations, stored snapshots, and replay against historical data.

Typical checks:
- old data still loads or fails explicitly
- migration preserves required fields
- reprocessing produces consistent state

### 10. `REGRESSION_PERFORMANCE`
Use for previous bugs, release gates, burst or load behavior, and latency-sensitive paths.

Typical checks:
- fixed bug stays fixed
- high-volume path still preserves invariants
- no obvious throughput regression on critical loops

## Risk tags
Use one or more of:
- `MONEY_IMPACT`
- `LIVE_SAFETY`
- `DATA_LOSS`
- `STATE_CORRUPTION`
- `USER_VISIBLE_BREAK`
- `BACKWARD_COMPATIBILITY`
- `ASYNC_RACE`
- `OPERATOR_ERROR`

Risk tags do not replace scenario types. They are modifiers used for prioritization and escalation.

## Minimum scenario types by change category

| Change category | Required scenario types |
| --- | --- |
| Strategy DSL change | `CONTRACT`, `NOMINAL_FLOW`, `BOUNDARY_VALIDATION`, `SYNC_CONSISTENCY`, `REGRESSION_PERFORMANCE` |
| Execution / fill logic change | `NOMINAL_FLOW`, `STATE_TRANSITION`, `TEMPORAL_ORDERING`, `FAILURE_RECOVERY`, `SAFETY_GUARD`, `REGRESSION_PERFORMANCE` |
| Event processing change | `NOMINAL_FLOW`, `TEMPORAL_ORDERING`, `FAILURE_RECOVERY`, `REGRESSION_PERFORMANCE` |
| DB schema change | `CONTRACT`, `PERSISTENCE_COMPATIBILITY`, `BOUNDARY_VALIDATION`, `REGRESSION_PERFORMANCE` |
| API contract change | `CONTRACT`, `NOMINAL_FLOW`, `BOUNDARY_VALIDATION`, `SYNC_CONSISTENCY`, `REGRESSION_PERFORMANCE` |
| Monitoring UI change | `NOMINAL_FLOW`, `BOUNDARY_VALIDATION`, `SYNC_CONSISTENCY`, `REGRESSION_PERFORMANCE`, plus `SAFETY_GUARD` if `LIVE` interactions are involved |
| UI visual / design system change | `NOMINAL_FLOW`, `BOUNDARY_VALIDATION`, `SYNC_CONSISTENCY`, `REGRESSION_PERFORMANCE`, plus `SAFETY_GUARD` if `LIVE` warnings, danger affordances, or confirmation cues changed |
| Coding convention / architecture change | `NOMINAL_FLOW`, `REGRESSION_PERFORMANCE`, plus `FAILURE_RECOVERY` when runtime behavior changes |

When logging, tracing, or monitoring behavior is affected, extend `NOMINAL_FLOW` or `FAILURE_RECOVERY` scenarios with explicit log and trace assertions.

## Scenario generation heuristics
- One new input branch requires at least one `NOMINAL_FLOW` and one `BOUNDARY_VALIDATION` scenario.
- One new state transition requires at least one allowed-transition and one rejected-transition scenario.
- One timeout, reconnect, dedupe, or retry rule requires at least one `TEMPORAL_ORDERING` and one `FAILURE_RECOVERY` scenario.
- One destructive operation requires at least one `SAFETY_GUARD` scenario.
- One schema, payload, or storage shape change requires at least one `CONTRACT` and one `PERSISTENCE_COMPATIBILITY` scenario.
- One shared visual pattern, token, or alert treatment change requires at least one `REGRESSION_PERFORMANCE` scenario across every impacted screen family.
- One user-visible fix requires at least one `REGRESSION_PERFORMANCE` scenario that proves the old bug no longer reproduces.

## Example scenario packs

Use `AI_SCENARIO_CATALOG.md` as the default source for category-specific packs and richer expected-result templates.

### Execution / fill logic change
- `SCN-EXE-NOM-001`
  - type: `NOMINAL_FLOW`
  - maps to: `TC-BT-001`
  - check: market order entry applies fee and slippage exactly
- `SCN-EXE-TIME-001`
  - type: `TEMPORAL_ORDERING`
  - maps to: `TC-BT-004`
  - check: same-candle TP and SL follows documented priority
- `SCN-EXE-FAIL-001`
  - type: `FAILURE_RECOVERY`
  - maps to: `TC-BT-003`
  - check: unfilled limit order cancels and falls back to market exactly once
- `SCN-EXE-SAFE-001`
  - type: `SAFETY_GUARD`
  - maps to: `TC-EXE-001`
  - check: emergency stop blocks new orders and records the rejection reason

### Event processing change
- `SCN-EVT-NOM-001`
  - type: `NOMINAL_FLOW`
  - maps to: `TC-EVT-001`
  - check: duplicate events are suppressed without losing the first valid event
- `SCN-EVT-TIME-001`
  - type: `TEMPORAL_ORDERING`
  - maps to: `TC-EVT-002`
  - check: out-of-order trades are processed by `event_time + sequence_no`
- `SCN-EVT-FAIL-001`
  - type: `FAILURE_RECOVERY`
  - maps to: `TC-EVT-003`
  - check: reconnect gap recovery moves the system to recovered or degraded state with logs
- `SCN-EVT-REG-001`
  - type: `REGRESSION_PERFORMANCE`
  - maps to: `suite_release_gate`
  - check: burst traffic preserves dedupe and ordering invariants

### DSL or API contract change
- `SCN-CONTRACT-001`
  - type: `CONTRACT`
  - maps to: `TC-API-001`
  - check: request and response shapes match the updated spec exactly
- `SCN-DSL-BOUNDARY-001`
  - type: `BOUNDARY_VALIDATION`
  - maps to: `TC-DSL-002`, `TC-DSL-003`
  - check: missing required fields and unknown operators fail with documented errors
- `SCN-DSL-SYNC-001`
  - type: `SYNC_CONSISTENCY`
  - maps to: `TC-UI-004`
  - check: form state, JSON preview, and backend validator agree on the latest valid shape

## When the AI must ask the user
Ask the user instead of deciding alone when:
- two or more product behaviors are plausible from the current docs
- the fix would relax a safety constraint or risk guard
- the change requires destructive migration, deletion, or irreversible backfill
- the desired behavior contradicts higher-priority SSOT docs
- validation can only pass by narrowing scope in a user-visible way
- the task changes economic behavior, order priority, or other money-impacting rules beyond a clearly documented spec

## Scenario card template

```md
- scenario_id: SCN-XXX-001
- change_category: Execution / fill logic change
- scenario_type: TEMPORAL_ORDERING
- risk_tags: MONEY_IMPACT, STATE_CORRUPTION
- modes: BACKTEST, PAPER
- source_docs: EXECUTION_SIMULATION_SPEC.md, TEST_CASES.md
- mapped_test_ids: TC-BT-004
- preconditions: Open position with TP and SL both reachable in one candle
- action: Run the execution path for the conflicting candle
- expected_result: The engine applies the documented TP/SL priority and emits deterministic logs
- verification_method: automated test plus log assertion
- result: PASS | PARTIAL_PASS | FAIL | BLOCKED
- root_cause_if_not_pass: SPEC_GAP | IMPLEMENTATION_DEFECT | TEST_OR_FIXTURE_DEFECT | ENVIRONMENT_BLOCKER | LEGACY_BEHAVIOR_MISMATCH
- next_action: patch code | patch docs | rerun | ask user
```

## Completion rule
A maintenance task is not complete until:
- required scenarios were generated
- required scenarios were validated or explicitly marked blocked
- the action taken matches the validation result
- docs, tests, and changelog were updated in the same work unit
