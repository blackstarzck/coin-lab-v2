# STATE_MACHINE.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

참조:
- 실행 규칙: [EXECUTION_SIMULATION_SPEC.md](./EXECUTION_SIMULATION_SPEC.md)
- 저장소 enum: [DB_SCHEMA_SQL_LEVEL.md](./DB_SCHEMA_SQL_LEVEL.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

## 1. Session State
- PENDING
- RUNNING
- STOPPING
- STOPPED
- FAILED

전이:
- PENDING -> RUNNING
- RUNNING -> STOPPING -> STOPPED
- PENDING -> FAILED
- RUNNING -> FAILED

규칙:
- 세션은 단일 `strategy_version_id`에 귀속된다
- emergency kill은 별도 session enum을 만들지 않고 `STOPPING` 전이 + risk event / reason field로 표현한다
- pause/resume 기능을 재도입할 경우 `PRE_IMPLEMENTATION_CONFLICTS.md`와 DB/API/UI 문서를 먼저 갱신한다

## 2. Position State
- NONE
- OPENING
- OPEN
- CLOSING
- CLOSED
- FAILED

규칙:
- strategy_version + symbol 단위 활성 포지션은 1개
- OPENING 중 추가 ENTRY 금지
- CLOSING 중 추가 EXIT 금지

## 3. Order State
- CREATED
- SUBMITTED
- PARTIALLY_FILLED
- FILLED
- CANCELLED
- REJECTED
- EXPIRED
- FAILED

규칙:
- 주문 접수 이후 미체결 대기 상태는 `SUBMITTED`로 유지한다
- 취소 요청 중간 단계는 별도 enum 대신 로그/이벤트로 추적한다

## 4. Execution Mode
- BACKTEST
- PAPER
- LIVE

규칙:
- 활성 세션에서 모드 변경 금지
- 모드 변경은 새 세션 생성으로 처리

## 5. Risk State
- CLEAR
- WARNING
- BLOCKED
- KILL_SWITCHED

## 6. Reentry State
- ELIGIBLE
- COOLDOWN
- WAIT_RESET
- DISABLED

## 7. 중요 불변 조건
- OPEN 상태에서는 새 ENTRY 금지
- session이 RUNNING이 아니면 actionable signal 금지
- BACKTEST/PAPER/LIVE는 같은 포지션 ID를 공유하지 않음
