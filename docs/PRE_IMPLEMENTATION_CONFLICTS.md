# PRE_IMPLEMENTATION_CONFLICTS

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 목적
이 문서는 구현 착수 전에 반드시 정리해야 하는 문서 충돌, 애매한 정의, 구조적 갈림길을 정리한 선행 명세다.
본 문서의 목적은 다음과 같다.

- Codex 또는 다른 구현 에이전트가 문서 간 차이를 임의 해석하지 못하게 한다.
- 구현 전에 반드시 통일해야 하는 상태값, API 규칙, 세션 모델을 고정한다.
- 어떤 문서를 어떤 순서로 수정해야 하는지 작업 기준을 제공한다.
- 충돌을 해결하지 않은 상태에서 구현에 들어가 생길 수 있는 재작업 비용을 줄인다.

## 적용 범위
본 문서는 아래 문서보다 우선하여 **사전 충돌 정리 기준**으로 사용한다.

- STATE_MACHINE.md
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- API_SPEC.md
- API_PAYLOADS.md
- API_CONTRACTS.md
- ERROR_CODE_SPEC.md
- MONITORING_SCREEN_SPEC.md
- STRATEGY_DSL_SPEC.md
- ARCHITECTURE.md
- UI_IA.md

구현 에이전트는 본 문서에서 지정한 최종 결정 사항을 먼저 관련 문서에 반영한 후 구현을 시작해야 한다.

---

## 최우선 원칙

1. 문서에 없는 enum, field, operator, state transition을 임의로 추가하지 않는다.
2. 상태값은 DB, API, 프론트, 테스트에서 동일한 문자열을 사용한다.
3. 실행 단위는 단일 전략 세션으로 고정한다.
4. 비교 단위는 UI에서 여러 세션을 병렬로 표시하는 방식으로 고정한다.
5. API는 `/api/v1/...` 경로와 공통 envelope 규칙을 사용한다.
6. 전략 정의 JSON은 TypeScript, Pydantic, DB json shape가 동일해야 한다.
7. 충돌 해결 전 구현 금지. 충돌 발견 시 본 문서 또는 관련 문서를 먼저 수정한다.

---

# P0. 구현 전 반드시 해결해야 하는 충돌

## P0-1. 상태머신 상태값 ↔ DB enum ↔ API 상태 문자열 통일

### 관련 문서
- STATE_MACHINE.md
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- API_SPEC.md
- API_PAYLOADS.md
- MONITORING_SCREEN_SPEC.md
- TEST_CASES.md

### 문제
현재 문서 세트는 상태의 개념은 대체로 일치하지만, 구현 시 다음과 같은 혼용 위험이 있다.

- running / active / started
- failed / error
- stopped / paused / terminated
- pending / queued / initializing
- completed / finished

이 상태로 구현에 들어가면 아래 문제가 발생한다.

- DB enum 값과 프론트 뱃지 값이 달라진다.
- 상태 전이 테스트가 문서마다 다르게 작성된다.
- API payload의 상태 문자열과 내부 엔진 상태가 달라질 수 있다.
- UI 필터와 백엔드 검색 조건이 어긋난다.

### 최종 결정
상태값은 엔티티별로 독립 enum을 사용하며, 각 enum은 문자열을 그대로 DB/API/UI/테스트에서 공유한다.

#### session_state
- `PENDING`
- `RUNNING`
- `STOPPING`
- `STOPPED`
- `FAILED`

#### position_state
- `NONE`
- `OPENING`
- `OPEN`
- `CLOSING`
- `CLOSED`
- `FAILED`

#### order_state
- `CREATED`
- `SUBMITTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELLED`
- `REJECTED`
- `EXPIRED`
- `FAILED`

#### signal_state
- `GENERATED`
- `ACCEPTED`
- `REJECTED`
- `EXPIRED`
- `CONSUMED`

#### backtest_run_state
- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

#### execution_mode
- `BACKTEST`
- `PAPER`
- `LIVE`

### 상태 전이 원칙
- 세션은 `PENDING -> RUNNING -> STOPPING -> STOPPED`를 기본 흐름으로 한다.
- 오류 발생 시 세션은 `FAILED`로 전이될 수 있다.
- 포지션은 `NONE -> OPENING -> OPEN -> CLOSING -> CLOSED` 흐름을 기본으로 한다.
- 주문은 `CREATED -> SUBMITTED -> PARTIALLY_FILLED/FILLED/CANCELLED/REJECTED/EXPIRED/FAILED` 흐름을 가진다.
- 상태 전이는 STATE_MACHINE.md를 SSOT로 상세화하되, 문자열 값은 본 문서와 동일해야 한다.

### 영향 범위
- DB enum migration
- API response schema
- React badge/filter constants
- monitoring UI 상태 표시
- 테스트 fixture 상태값

### 수정 대상 문서
- STATE_MACHINE.md
- DB_SCHEMA_SQL_LEVEL.md
- DB_SCHEMA.md
- API_PAYLOADS.md
- MONITORING_SCREEN_SPEC.md
- TEST_CASES.md
- ERROR_CODE_SPEC.md

---

## P0-2. API path 규칙 ↔ success/error envelope 규칙 통일

### 관련 문서
- API_CONTRACTS.md
- API_SPEC.md
- API_PAYLOADS.md
- ERROR_CODE_SPEC.md

### 문제
API 문서가 목록과 payload를 분리해서 설명하고 있기 때문에, 구현 에이전트가 다음을 임의 결정할 수 있다.

- base path (`/api/v1`, `/api`, `/strategies` 혼용)
- resource naming 규칙
- success response envelope 유무
- error response envelope 구조
- `trace_id`와 `timestamp`의 위치

### 최종 결정
모든 API는 `/api/v1/...` 경로를 사용한다.

#### path 규칙
- collection: `/api/v1/strategies`
- item: `/api/v1/strategies/{strategyId}`
- nested resource: `/api/v1/strategies/{strategyId}/versions`
- actions: `/api/v1/backtests/run`, `/api/v1/sessions/{sessionId}/stop`

#### success envelope
```json
{
  "success": true,
  "data": {},
  "meta": {},
  "trace_id": "trc_...",
  "timestamp": "2026-03-11T12:00:00.000Z"
}
```

#### error envelope
```json
{
  "success": false,
  "error_code": "API-VALIDATION-001",
  "message": "Human readable summary",
  "details": {},
  "trace_id": "trc_...",
  "timestamp": "2026-03-11T12:00:00.000Z"
}
```

#### pagination meta
- `page`
- `page_size`
- `total`
- `has_next`

#### 시간 포맷
- API 외부 노출 시간은 UTC ISO 8601 문자열로 통일한다.

### 영향 범위
- FastAPI response model
- frontend API client
- error handling hook
- toast/logging UI
- contract tests

### 수정 대상 문서
- API_CONTRACTS.md
- API_SPEC.md
- API_PAYLOADS.md
- ERROR_CODE_SPEC.md
- CODING_GUIDELINES.md

---

## P0-3. 단일 전략 세션 vs 다중 전략 세션 확정

### 관련 문서
- ARCHITECTURE.md
- STATE_MACHINE.md
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- MONITORING_SCREEN_SPEC.md
- UI_IA.md

### 문제
요구사항에는 복수 전략 실시간 비교가 들어가 있으므로, 구현 에이전트가 다음 두 가지를 혼동할 가능성이 있다.

- 실행 세션 하나에 여러 전략을 묶는 방식
- 전략 하나당 세션 하나를 두고 UI에서 비교하는 방식

이 결정을 미루면 아래가 전부 흔들린다.

- live_sessions 테이블 구조
- session state machine
- 로그 귀속 방식
- risk guard 범위
- monitoring layout

### 최종 결정
- **실행 단위는 단일 전략 세션**이다.
- 세션 1개는 정확히 다음을 가진다.
  - strategy_version_id 1개
  - execution_mode 1개
  - candidate_universe_config 1개
- **비교 단위는 UI 레벨의 다중 세션 병렬 표시**다.
- 모니터링 화면은 최대 4개 세션을 병렬 비교할 수 있다.
- 세션끼리 상태, 로그, 포지션, 주문, 성과는 독립적으로 관리한다.

### 파생 결정
- `live_sessions` 또는 `strategy_sessions`는 strategy_version_id를 FK로 가진다.
- comparison workspace가 필요하면 별도 UI 상태로만 관리하고, 실행 엔진의 세션 개념과 섞지 않는다.

### 수정 대상 문서
- ARCHITECTURE.md
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- STATE_MACHINE.md
- MONITORING_SCREEN_SPEC.md
- UI_IA.md

---

# P1. 구현 직후 어긋나기 쉬운 충돌

## P1-1. 전략 DSL 필드명 ↔ 저장 payload ↔ DB json shape 통일

### 관련 문서
- STRATEGY_SCHEMA.md
- STRATEGY_DSL_SPEC.md
- API_PAYLOADS.md
- DB_SCHEMA_SQL_LEVEL.md

### 문제
전략 JSON을 사람이 읽기 쉽게 설계했지만, form + JSON sync 편집, validator, DB 저장 구조가 정확히 같지 않으면 곧바로 꼬인다.

### 최종 결정
아래 3개는 동일 구조를 공유해야 한다.
- TypeScript strategy type
- Pydantic strategy schema
- DB `strategy_definition_json` shape

### 필수 최상위 필드
- `id`
- `name`
- `type`
- `schema_version`
- `market`
- `universe`
- `entry`
- `reentry`
- `position`
- `exit`
- `risk`
- `execution`
- `backtest`

### 추가 원칙
- DSL operator 이름은 STRATEGY_DSL_SPEC.md만을 기준으로 한다.
- form UI 필드명은 JSON key와 1:1 대응한다.
- 설명용 label은 달라도 내부 key는 바꾸지 않는다.
- explain/debug payload 구조도 API_PAYLOADS.md에 고정한다.

### 수정 대상 문서
- STRATEGY_DSL_SPEC.md
- STRATEGY_SCHEMA.md
- API_PAYLOADS.md
- DB_SCHEMA_SQL_LEVEL.md
- MONITORING_SCREEN_SPEC.md
- Resolved root shape:
  - no `meta` wrapper
  - canonical root keys come from STRATEGY_DSL_SPEC.md / STRATEGY_SCHEMA.md
  - optional root keys are `description`, `enabled`, `labels`, `notes`

---

## P1-2. PAPER / BACKTEST / LIVE 책임 분리

### 관련 문서
- EXECUTION_SIMULATION_SPEC.md
- STATE_MACHINE.md
- ERROR_CODE_SPEC.md
- TEST_CASES.md
- ARCHITECTURE.md

### 문제
모드 3개를 한 엔진에서 임의 분기하면 구현은 빨라 보이지만, 실거래 확장 시 구조가 망가진다.

### 최종 결정
- signal generation 규칙은 모드와 무관하게 최대한 공통화한다.
- PAPER와 BACKTEST는 동일한 체결 규칙을 공유하되, 데이터 입력 소스와 시뮬레이션 시간축만 다르다.
- LIVE는 실행 adapter를 별도로 두고, 주문 송신/응답/재시도/실패 처리를 infra 레벨에서 분리한다.
- execution_mode는 공통 파이프라인을 오염시키는 ad-hoc if 체인이 아니라, adapter 또는 strategy runner 조합으로 분리한다.

### 수정 대상 문서
- ARCHITECTURE.md
- EXECUTION_SIMULATION_SPEC.md
- STATE_MACHINE.md
- TEST_CASES.md
- CODING_GUIDELINES.md

---

## P1-3. signal ↔ order ↔ position 관계 정리

### 관련 문서
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- STATE_MACHINE.md
- EXECUTION_SIMULATION_SPEC.md

### 문제
signal, order, position의 관계를 느슨하게 적어 두면 partial fill, cancel/replace, duplicate signal 처리에서 바로 꼬인다.

### 최종 결정
- 하나의 signal은 0개 이상의 order attempt를 만들 수 있다.
- order fill 결과는 하나의 position을 open/update/close한다.
- position 귀속 단위는 `session_id + symbol`이다.
- partial fill은 order execution 레벨에서 관리한다.
- position은 복수 order를 누적 반영할 수 있다.

### 수정 대상 문서
- DB_SCHEMA.md
- DB_SCHEMA_SQL_LEVEL.md
- STATE_MACHINE.md
- EXECUTION_SIMULATION_SPEC.md
- TEST_CASES.md

---

# P2. 품질과 유지보수성을 좌우하는 충돌

## P2-1. 모니터링 화면 용어 ↔ 백엔드 필드 정합성

### 관련 문서
- MONITORING_SCREEN_SPEC.md
- UI_IA.md
- API_PAYLOADS.md

### 최종 결정
- UI에서 한국어/설명형 라벨을 사용할 수 있다.
- 그러나 내부 필드명, filter key, sort key는 API payload와 동일해야 한다.
- `status`, `mode`, `pnl`, `pnl_rate`, `signal_count`, `win_rate` 같은 키는 화면별로 이름을 바꾸지 않는다.

### 수정 대상 문서
- MONITORING_SCREEN_SPEC.md
- UI_IA.md
- API_PAYLOADS.md

---

## P2-2. 로그 분류와 필수 로그 필드 고정

### 관련 문서
- AGENT.md
- ENGINE_GUIDELINES.md
- ERROR_CODE_SPEC.md
- DOC_UPDATE_CHECKLIST.md

### 최종 결정
모든 핵심 로그는 최소 아래 필드를 포함한다.
- `timestamp`
- `trace_id`
- `mode`
- `strategy_version_id`
- `session_id`
- `symbol`
- `event_type`
- `result`
- `error_code` (optional)

### 표준 로그 분류
- system_logs
- market_ingest_logs
- strategy_execution_logs
- order_simulation_logs
- risk_control_logs
- document_change_logs
- agent_action_logs

### 수정 대상 문서
- AGENT.md
- ENGINE_GUIDELINES.md
- ERROR_CODE_SPEC.md
- DOC_UPDATE_CHECKLIST.md

---

## P2-3. 시간 필드 의미와 포맷 통일

### 관련 문서
- EVENT_PROCESSING_RULES.md
- API_PAYLOADS.md
- DB_SCHEMA_SQL_LEVEL.md
- TEST_CASES.md

### 최종 결정
시간은 의미별로 분리한다.
- `exchange_event_time`: 거래소 이벤트 발생 시각
- `ingested_at`: 시스템 수신 시각
- `persisted_at`: 저장 시각
- `evaluated_at`: 전략 평가 시각
- `created_at` / `updated_at`: 레코드 관리 시각

외부 API 노출은 UTC ISO 8601 문자열을 사용한다.
내부 저장은 timestamp with timezone 또는 epoch ms를 허용하되, 문서상 의미는 동일해야 한다.

### 수정 대상 문서
- EVENT_PROCESSING_RULES.md
- API_PAYLOADS.md
- DB_SCHEMA_SQL_LEVEL.md
- TEST_CASES.md

---

# P3. 초기에 1차 고정이 필요한 선택 항목

## P3-1. candidate pool 기준

### 관련 문서
- ARCHITECTURE.md
- EVENT_FLOW.md
- EVENT_PROCESSING_RULES.md
- MONITORING_SCREEN_SPEC.md

### 1차 결정안
candidate pool은 아래 3개 집합의 합집합으로 정의한다.
- 사용자 고정 watchlist
- 최근 거래대금 상위 N 종목
- 단기 급등/급락/거래량 급증 탐지 종목

### 추가 규칙
- refresh 주기는 이벤트 처리 규칙 문서에 명시한다.
- candidate pool 자체는 실행 세션과 분리된 입력 데이터다.

### 수정 대상 문서
- ARCHITECTURE.md
- EVENT_FLOW.md
- EVENT_PROCESSING_RULES.md
- MONITORING_SCREEN_SPEC.md

---

## P3-2. Kelly sizing 기본 적용 방식

### 관련 문서
- EXECUTION_SIMULATION_SPEC.md
- STRATEGY_DSL_SPEC.md
- TEST_CASES.md

### 1차 결정안
- Fractional Kelly 사용
- 최소/최대 포지션 비율 캡 적용
- 신뢰도 부족 시 fallback fixed percent 허용
- MVP에서는 자동 적용하되, UI에 계산 근거와 최종 적용 비율을 표시한다.

### 수정 대상 문서
- EXECUTION_SIMULATION_SPEC.md
- STRATEGY_DSL_SPEC.md
- TEST_CASES.md
- MONITORING_SCREEN_SPEC.md

---

# 구현 착수 전 필수 수정 순서

## 1단계
아래 문서를 먼저 수정한다.
- STATE_MACHINE.md
- DB_SCHEMA_SQL_LEVEL.md
- API_PAYLOADS.md
- API_CONTRACTS.md
- ERROR_CODE_SPEC.md

## 2단계
아래 문서를 정합성 맞추기 위해 수정한다.
- DB_SCHEMA.md
- ARCHITECTURE.md
- MONITORING_SCREEN_SPEC.md
- STRATEGY_DSL_SPEC.md
- STRATEGY_SCHEMA.md

## 3단계
운영/검증 문서를 보강한다.
- TEST_CASES.md
- DOC_UPDATE_CHECKLIST.md
- AGENT.md
- CHANGELOG_AGENT.md

---

# Codex 작업 지시 규칙

구현 에이전트는 다음 순서를 따라야 한다.

1. 본 문서를 읽는다.
2. 본 문서의 최종 결정 사항을 관련 문서에 반영할 수정 목록을 작성한다.
3. 문서를 먼저 수정한다.
4. 변경된 문서 기준으로 gap analysis를 다시 작성한다.
5. 그 후에만 구현을 시작한다.

아래 사항은 금지한다.
- 문서 수정 없이 enum/state를 코드에 먼저 반영하는 행위
- 단일 전략 세션 결정을 무시하고 다중 전략 세션 엔진을 만드는 행위
- `/api/v1` 외 경로 체계를 임의로 섞는 행위
- 상태 문자열을 UI 편의상 임의 변형하는 행위
- strategy_definition JSON 구조를 frontend/backend에서 다르게 정의하는 행위

---

# 변경 이력
- v1.0: 구현 전 충돌 정리 초안 작성
