# DOC_UPDATE_CHECKLIST.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document defines which documents must be reviewed and updated whenever a specific class of change is made.

This is a mandatory checklist for both humans and AI agents.

## Universal rule
If code behavior changes and the relevant spec is not updated in the same work unit, the task is incomplete.

If a screen's visual style, shared component pattern, token, or state presentation changes, `DESIGN_SYSTEM.md` must be reviewed as part of the same work unit.

Every `docs/*.md` file must start with the standard `## 문서 정보` block and include a `CHANGELOG_AGENT.md` link so document ownership, status, and update history can be checked quickly.

Any documentation update must be reflected in `CHANGELOG_AGENT.md` within the same work unit.

## Change categories

### 1. Strategy DSL change
Examples:
- new operator added
- operator fields changed
- validation behavior changed
- plugin contract changed

**Must update:**
- `STRATEGY_DSL_SPEC.md`
- `API_PAYLOADS.md` (if validation or payload changes)
- `DB_SCHEMA_SQL_LEVEL.md` (if stored JSON shape changes)
- `TEST_CASES.md`
- `CHANGELOG_AGENT.md`
- `DECISIONS.md` (if architectural)

### 2. Execution / fill logic change
Examples:
- fee calculation changed
- slippage changed
- fallback-to-market changed
- TP/SL priority changed

**Must update:**
- `EXECUTION_SIMULATION_SPEC.md`
- `TEST_CASES.md`
- `ERROR_CODE_SPEC.md` (if new error/risk code introduced)
- `API_PAYLOADS.md` (if payload fields changed)
- `CHANGELOG_AGENT.md`

### 3. Event processing change
Examples:
- reconnect policy changed
- reorder window changed
- stale thresholds changed
- snapshot trigger changed

**Must update:**
- `EVENT_PROCESSING_RULES.md`
- `EVENT_FLOW.md`
- `TEST_CASES.md`
- `ERROR_CODE_SPEC.md`
- `MONITORING_SCREEN_SPEC.md` (if UI status changes)
- `CHANGELOG_AGENT.md`

### 4. DB schema change
Examples:
- table/column added
- enum changed
- new index or FK added
- JSON schema changed

**Must update:**
- `DB_SCHEMA_SQL_LEVEL.md`
- `PERSISTENCE_ALIGNMENT_ADDENDUM.md` (if the change adds or overrides the final persistence alignment rules)
- migration SQL files
- `API_PAYLOADS.md` (if contract affected)
- `TEST_CASES.md` (if behavior affected)
- `CHANGELOG_AGENT.md`

### 5. API contract change
Examples:
- new field in response
- request validation changed
- endpoint added
- pagination changed

**Must update:**
- `API_PAYLOADS.md`
- `ERROR_CODE_SPEC.md`
- `TEST_CASES.md`
- frontend types/contracts
- `CHANGELOG_AGENT.md`

### 6. Monitoring UI change
Examples:
- widget added
- table column changed
- new live warning badge
- route changed

**Must update:**
- `MONITORING_SCREEN_SPEC.md`
- `UI_IA.md`
- `DESIGN_SYSTEM.md` (if visual treatment, token usage, state chip, panel composition, or shared component style changed)
- `AI_UI_STYLE_GUIDE.md` (if the change introduces or revises a reusable UI pattern)
- `TEST_CASES.md`
- `CHANGELOG_AGENT.md`

### 7. UI visual / design system change
Examples:
- color token changed
- card/button/input/table styling changed
- app shell or navigation styling changed
- new reusable screen composition pattern introduced

**Must update:**
- `DESIGN_SYSTEM.md`
- `AI_UI_STYLE_GUIDE.md`
- `UI_IA.md` (if route-level composition changed)
- `MONITORING_SCREEN_SPEC.md` (if monitoring visual behavior changed)
- `CHANGELOG_AGENT.md`

### 8. Coding convention / architecture change
Examples:
- Zustand/React Query boundary changed
- Python layer boundary changed
- logging policy changed

**Must update:**
- `CODING_GUIDELINES.md`
- `ARCHITECTURE.md`
- `AGENT.md`
- `DECISIONS.md`
- `CHANGELOG_AGENT.md`

## PR / task completion checklist
Before marking a task done, confirm:
- [ ] I identified the primary change category
- [ ] I generated the required scenario types for the change
- [ ] I wrote explicit expected results before validating the scenarios
- [ ] I validated the required scenarios or explicitly recorded blockers
- [ ] I updated all required documents for that category
- [ ] I checked whether `DESIGN_SYSTEM.md` or `AI_UI_STYLE_GUIDE.md` also changed
- [ ] I added or mapped at least one relevant test case
- [ ] I updated error codes if behavior changed
- [ ] I updated changelog entry
- [ ] I checked whether architecture decisions changed

## AI-specific rule
AI agents must not silently infer “no doc update needed” for behavior-changing work. They must state one of:
- documents updated
- no document impact, with reason
- blocked due to missing authority/spec
For scenario generation, expected-result definition, validation, and result handling, follow `AI_MAINTENANCE_WORKFLOW.md` and `AI_SCENARIO_CATALOG.md`.

## Minimum changelog entry format
Every behavior-changing task must append a changelog entry including:
- date/time
- files changed
- behavior summary
- impacted modes (`BACKTEST`, `PAPER`, `LIVE`)
- spec documents updated
- test cases added/updated
