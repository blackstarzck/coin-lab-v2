# CODEX_MASTER_PROMPT

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Usage Order
Use the prompts in this order:
1. Paste the **Main Prompt** first.
2. Paste the **Phase Prompt** for the current step.
3. Add the **Additional Rules** block.
4. Require Codex to report changed files, assumptions, unresolved issues, and document updates after each phase.

---

## Main Prompt

```md
You are working on a local-first but web-expandable crypto strategy lab / trading console project.

## Project Goal
Build a high-quality MVP for a coin strategy lab that:
- monitors Upbit market flow in real time
- manages multiple strategies
- runs backtests on historical data
- compares strategies in real time
- supports PAPER and LIVE expansion later
- prioritizes responsiveness, maintainability, modularity, reusability, and correctness

## Core Tech Stack
- Frontend: React, TypeScript, MUI, lightweight-charts, React Query, Zustand
- Backend: Python, FastAPI
- Workers: Python async workers
- Database: Supabase
- Environment: Windows local development first
- No NestJS in MVP unless explicitly requested later

## Critical Instruction
You must treat the provided markdown documents as the source of truth.
Do not invent architecture, schema, payload fields, operator names, or flow rules beyond the docs.
If something is missing or conflicting:
1. stop
2. identify the exact gap
3. propose the minimum change needed
4. update the relevant documents first
5. only then continue implementation

If `PRE_IMPLEMENTATION_CONFLICTS.md` defines a final decision for the topic:
1. treat it as the pre-implementation authority
2. update the affected target docs first
3. continue implementation only after the lower docs reflect that decision

## Document Priority Order
Use documents in this exact precedence order when conflicts occur:

1. PRE_IMPLEMENTATION_CONFLICTS.md
2. CODING_GUIDELINES.md
3. STRATEGY_DSL_SPEC.md
4. EXECUTION_SIMULATION_SPEC.md
5. API_PAYLOADS.md
6. DB_SCHEMA_SQL_LEVEL.md
7. PERSISTENCE_ALIGNMENT_ADDENDUM.md
8. MONITORING_SCREEN_SPEC.md
9. EVENT_PROCESSING_RULES.md
10. ERROR_CODE_SPEC.md
11. TEST_CASES.md
12. DOC_UPDATE_CHECKLIST.md
13. AI_MAINTENANCE_WORKFLOW.md
14. AI_SCENARIO_CATALOG.md
15. AGENT.md
16. ARCHITECTURE.md
17. EVENT_FLOW.md
18. STATE_MACHINE.md
19. DB_SCHEMA.md
20. API_SPEC.md
21. UI_IA.md
22. TEST_STRATEGY.md
23. DECISIONS.md
24. DOC_INDEX.md

If higher-priority docs and lower-priority docs differ, follow the higher-priority one.

## UI Visual Priority
For frontend screens and shared UI components, use this additional order:

1. DESIGN_SYSTEM.md for color, typography, spacing, surface, component look and feel
2. AI_UI_STYLE_GUIDE.md for layout, density, hierarchy, and consistency guardrails
3. UI_IA.md for route-level structure and information architecture
4. MONITORING_SCREEN_SPEC.md for monitoring-specific behavior and widget composition

## Product Constraints
- Strategy execution is symbol-independent
- Strategy definition supports JSON DSL + Python plugin hybrid
- Monitoring candidates are dynamic candidate pools
- Max concurrent strategy comparison target is 4
- Watch target is volume/top movers/watchlist-based dynamic set
- Modes: BACKTEST / PAPER / LIVE
- No login in MVP
- Live trading safety must be strict
- Live/Paper/Backtest behavior must not be mixed carelessly
- UI must support form + JSON synchronized strategy editing
- Kelly-based position sizing should use fractional Kelly with safety caps

## Non-Negotiable Engineering Rules
- Do not put strategy evaluation logic inside React components
- Do not use React components as data orchestration layers
- Do not duplicate server state into Zustand unless explicitly justified
- Do not create undocumented enum values or undocumented JSON fields
- Do not implement undocumented DSL operators
- Do not mix LIVE / PAPER / BACKTEST execution logic in one ad-hoc branch-heavy module
- Do not skip logs for signal generation, execution attempts, rejection reasons, or risk blocking
- Do not implement WebSocket handling without reconnection, dedupe, and stale-state rules
- Do not implement backtest fills in a simplistic way that contradicts EXECUTION_SIMULATION_SPEC.md
- Do not proceed with implementation if request/response shapes are unspecified; update docs first

## Required Architecture Style
### Frontend
Use feature-oriented structure with:
- app
- pages
- widgets
- features
- entities
- shared
- stores only for client UI state
- React Query for server state
- custom hooks for data/use cases
- lightweight-charts adapter isolated from page logic

### Backend
Use Python layered structure:
- domain
- application
- infrastructure
- api
- workers
- schemas

Keep:
- domain logic pure where possible
- Pydantic schemas explicit
- retry/timeout/cancellation rules explicit
- trace_id propagation
- structured logging
- clear service boundaries

## Required Delivery Style
Implement in small, reviewable stages.
For each stage:
1. explain what will be changed
2. list affected files
3. implement
4. explain what assumptions were made
5. list which docs should be updated
6. update docs if needed

## Mandatory First Task
Before coding, do the following:

1. Read `PRE_IMPLEMENTATION_CONFLICTS.md` first
2. Read all remaining provided markdown docs
3. Produce a gap analysis with sections:
   - Missing definitions
   - Conflicting definitions
   - Risky ambiguities
   - Items that would cause incorrect implementation
4. Produce an implementation plan in phases
5. Wait for approval only if the docs are critically insufficient
6. Otherwise begin Phase 1

## Implementation Phases
Use this order unless docs require adjustment:

### Phase 1
Foundation and schema alignment
- repository structure
- backend app skeleton
- frontend app skeleton
- shared types
- Supabase schema/migrations aligned to DB_SCHEMA_SQL_LEVEL.md and PERSISTENCE_ALIGNMENT_ADDENDUM.md
- error code constants
- base logging and trace id utilities

### Phase 2
Strategy definition foundation
- DSL schema validation
- strategy storage/retrieval
- strategy versioning
- plugin interface contract
- strategy explain/debug payload structure

### Phase 3
Market event ingestion
- Upbit websocket adapter
- normalization layer
- dedupe
- reconnect
- stale snapshot handling
- candidate pool generation
- market snapshot production

### Phase 4
Execution foundation
- signal generation pipeline
- PAPER execution engine
- BACKTEST execution engine
- fill simulation per EXECUTION_SIMULATION_SPEC.md
- risk guard hooks
- order/position/session state transitions

### Phase 5
Frontend monitoring and management UI
- dashboard
- strategy list
- strategy detail
- strategy editor (form + JSON sync)
- monitoring screen
- backtest run/result screen

### Phase 6
Testing and hardening
- test fixtures
- Given/When/Then cases
- event disorder/reconnect tests
- API contract validation
- execution simulation regression tests

## Required Outputs
At every meaningful checkpoint, provide:
- changed file tree
- summary of completed scope
- unresolved issues
- doc updates needed
- next recommended step

## If You Need to Make a Decision
Use this rule:
- If docs already imply the answer, follow the docs
- If docs conflict, follow the higher-priority doc and record the issue
- If docs are silent, propose the narrowest possible addition and update docs before coding

## Coding Quality Standard
Code must be:
- modular
- typed
- testable
- minimally stateful
- observable via logs
- safe under retry/reconnect/out-of-order conditions
- easy to extend later to real trading

## Final Reminder
This is not a prototype-only toy app.
Build it as a serious trading-console foundation.
Favor correctness, traceability, explicit contracts, and clean boundaries over speed or cleverness.
```

---

## Phase 1 Prompt

```md
Start with Phase 1 only.

Tasks:
1. Read all markdown documents in the project
2. Produce a structured gap analysis
3. Produce a concrete Phase 1 file/folder plan
4. Create the initial repository skeleton for:
   - frontend
   - backend
   - workers
   - infra
   - docs
5. Create initial backend and frontend bootstrap files
6. Create base shared constants for:
   - execution modes
   - error codes
   - trace id
   - timestamps
7. Create initial SQL migration files aligned strictly with DB_SCHEMA_SQL_LEVEL.md and PERSISTENCE_ALIGNMENT_ADDENDUM.md
8. Do not implement full business logic yet
9. Do not invent extra tables, operators, or API fields outside the docs
10. After implementation, summarize:
   - what was created
   - what remains unresolved
   - which docs should be updated

Important:
If any DB or API ambiguity blocks accurate implementation, stop and report the ambiguity clearly before proceeding.
```

---

## Phase 2 Prompt

```md
Proceed to Phase 2 only.

Tasks:
1. Implement strategy DSL validation layer
2. Implement JSON schema / Pydantic schema / TypeScript type alignment
3. Implement strategy CRUD foundation
4. Implement strategy versioning foundation
5. Implement plugin strategy interface contract
6. Implement explain/debug payload structure
7. Add minimal tests for:
   - valid DSL
   - invalid operator
   - invalid nested conditions
   - missing required fields
   - unsupported timeframe references

Constraints:
- Follow STRATEGY_DSL_SPEC.md exactly
- Do not invent operators
- Do not allow undocumented field names
- Keep form-compatible schema structure in mind
- If frontend and backend shape mismatch appears possible, identify it explicitly

Deliver:
- changed files
- schema explanation
- known gaps
- doc updates needed
```

---

## Phase 3 Prompt

```md
Proceed to Phase 3 only.

Tasks:
1. Implement Upbit WebSocket adapter
2. Implement raw event normalization
3. Implement dedupe rules
4. Implement reconnect handling
5. Implement stale snapshot invalidation
6. Implement candidate pool generation for dynamic monitoring
7. Implement market snapshot production
8. Add tests for:
   - duplicate event
   - reconnect
   - out-of-order event
   - stale snapshot discard
   - candidate pool refresh

Constraints:
- Follow EVENT_PROCESSING_RULES.md exactly
- Follow ERROR_CODE_SPEC.md for system/data errors
- Use structured logs and trace ids
- Do not connect raw exchange payloads directly to business logic
- Normalize first, then process

Deliver:
- changed files
- flow summary
- event model summary
- risk/edge cases still open
- doc updates needed
```

---

## Phase 4 Prompt

```md
Proceed to Phase 4 only.

Tasks:
1. Implement signal generation pipeline
2. Implement PAPER execution engine
3. Implement BACKTEST execution engine
4. Implement fill simulation according to EXECUTION_SIMULATION_SPEC.md
5. Implement order, position, and session state transitions
6. Implement risk guard hooks:
   - duplicate entry prevention
   - daily loss limit
   - max loss guard
   - emergency stop support
7. Add tests for:
   - market entry
   - limit entry with no fill
   - cancel/replace
   - fallback to market
   - stop loss
   - take profit
   - same-candle conflict handling
   - duplicate signal rejection

Constraints:
- PAPER and BACKTEST must share rule consistency where docs require it
- LIVE-specific behavior should not be stubbed incorrectly into PAPER/BACKTEST
- Log all execution decisions and rejection reasons
- Use error codes from ERROR_CODE_SPEC.md

Deliver:
- changed files
- state transition explanation
- simulation policy explanation
- unresolved behavior questions
- doc updates needed
```

---

## Phase 5 Prompt

```md
Proceed to Phase 5 only.

Tasks:
1. Implement dashboard page
2. Implement strategy list page
3. Implement strategy detail page
4. Implement strategy editor page with form + JSON sync
5. Implement monitoring screen according to MONITORING_SCREEN_SPEC.md
6. Implement backtest result screens
7. Use:
   - React Query for server state
   - Zustand only for UI/client state
   - MUI for layout/components
   - lightweight-charts via isolated adapter/components
8. Add loading, empty, and error states
9. Add LIVE mode warning UX and emergency stop UX placeholders

Constraints:
- No business logic inside presentational components
- No duplicated server cache in Zustand
- No undocumented filters, fields, or columns
- Monitoring layout must support up to 4 strategy comparisons
- Use memoization only where justified
- Keep effect usage minimal and explicit

Deliver:
- changed files
- page map
- component responsibility summary
- known UI gaps
- doc updates needed
```

---

## Additional Rules

```md
Additional Rules:
- Before changing schema, API, DSL, or state transitions, check DOC_UPDATE_CHECKLIST.md
- For behavior-changing maintenance work, generate, classify, and validate scenarios per AI_MAINTENANCE_WORKFLOW.md before finalizing
- Define explicit expected results for each scenario and use AI_SCENARIO_CATALOG.md as the default scenario-pack reference
- If a change touches DB, API, DSL, UI, or execution flow, update the corresponding docs in the same task
- Record architecture-impacting decisions in DECISIONS.md
- Record AI/doc-related changes in CHANGELOG_AGENT.md
- Never silently diverge code from docs
- If implementation reveals a missing rule, propose a doc patch before finalizing code
```
