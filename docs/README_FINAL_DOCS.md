# Coin Strategy Lab Final Docs Pack

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

This folder is the consolidated final document pack for the project.

## Included documents
- Project documentation stored under `docs/`
- Visual system SSOT: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- 1 Codex execution prompt document: [CODEX_MASTER_PROMPT.md](./CODEX_MASTER_PROMPT.md)

## Suggested use order
1. Read [DOC_INDEX.md](./DOC_INDEX.md) to understand the document graph.
2. Read [FIRST_RUN_GUIDE.md](./FIRST_RUN_GUIDE.md) before setting up a new environment or validating expected first-run behavior.
3. Read [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md) first when reconciling docs or starting implementation.
4. Read [DECISIONS.md](./DECISIONS.md) and [ARCHITECTURE.md](./ARCHITECTURE.md) for product and system direction.
5. Read [PRD.md](./PRD.md) for the consolidated product requirements, scope, user flows, and MVP boundaries.
6. If you are implementing frontend screens or UI components, read these UI/design docs before coding:
   - [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
   - [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md)
   - [UI_IA.md](./UI_IA.md)
   - [MONITORING_SCREEN_SPEC.md](./MONITORING_SCREEN_SPEC.md)
7. Read the implementation SSOT docs in priority order:
   - [CODING_GUIDELINES.md](./CODING_GUIDELINES.md)
   - [STRATEGY_DSL_SPEC.md](./STRATEGY_DSL_SPEC.md)
   - [EXECUTION_SIMULATION_SPEC.md](./EXECUTION_SIMULATION_SPEC.md)
   - [API_PAYLOADS.md](./API_PAYLOADS.md)
   - [DB_SCHEMA_SQL_LEVEL.md](./DB_SCHEMA_SQL_LEVEL.md)
   - [PERSISTENCE_ALIGNMENT_ADDENDUM.md](./PERSISTENCE_ALIGNMENT_ADDENDUM.md)
   - [MONITORING_SCREEN_SPEC.md](./MONITORING_SCREEN_SPEC.md)
   - [EVENT_PROCESSING_RULES.md](./EVENT_PROCESSING_RULES.md)
   - [ERROR_CODE_SPEC.md](./ERROR_CODE_SPEC.md)
   - [TEST_CASES.md](./TEST_CASES.md)
   - [DOC_UPDATE_CHECKLIST.md](./DOC_UPDATE_CHECKLIST.md)
8. Read [AI_MAINTENANCE_WORKFLOW.md](./AI_MAINTENANCE_WORKFLOW.md) for behavior-changing maintenance work and scenario validation.
9. Read [AI_SCENARIO_CATALOG.md](./AI_SCENARIO_CATALOG.md) for reusable scenario packs and expected-result patterns.
10. Use [CODEX_MASTER_PROMPT.md](./CODEX_MASTER_PROMPT.md) when starting implementation in Codex.
