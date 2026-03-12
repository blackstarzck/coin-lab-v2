# AGENT.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 목적
이 프로젝트를 수정하는 AI/개발자 공통 작업 규칙 문서.

## 핵심 원칙
- UI는 표시 계층, 전략 판단은 엔진 계층.
- 전략은 종목 독립형으로 평가한다.
- 전략 정의는 JSON DSL + Python plugin 혼합 구조.
- BACKTEST / PAPER / LIVE 모드는 분리 구현한다.
- 로그 없는 자동화와 문서 없는 스키마 변경은 금지한다.
- 실시간 시스템은 중복 이벤트, 순서 뒤바뀜, 재연결을 기본 전제로 설계한다.
- 차트는 반드시 업비트 기준에 맞춰 렌더링한다.

## 작업 전 확인
- 어떤 SSOT 문서가 관련되는가
- UI 작업이면 `DESIGN_SYSTEM.md`와 화면 명세 문서의 권한 경계를 확인했는가
- 전략/이벤트/DB/API/UI/테스트 영향 범위가 어디인가
- 중복 진입/잘못된 체결/재시도 꼬임 위험이 있는가
- 로그와 에러 처리 방안이 있는가

## 작업 후 확인
- 관련 문서를 갱신했는가
- CHANGELOG_AGENT.md에 기록했는가
- 영향 받는 테스트를 추가/수정했는가
- dedupe/idempotency 규칙을 위반하지 않았는가

## 문서 동기화 규칙
- 전략 DSL/validation 변경 -> STRATEGY_DSL_SPEC, API_PAYLOADS, DB_SCHEMA_SQL_LEVEL, TEST_CASES
- 이벤트/실시간 처리 변경 -> EVENT_PROCESSING_RULES, EVENT_FLOW, ERROR_CODE_SPEC, MONITORING_SCREEN_SPEC, TEST_CASES
- DB schema/persistence 변경 -> DB_SCHEMA_SQL_LEVEL, PERSISTENCE_ALIGNMENT_ADDENDUM, API_PAYLOADS, TEST_CASES
- API contract 변경 -> API_PAYLOADS, ERROR_CODE_SPEC, TEST_CASES, frontend types/contracts
- UI 시각/토큰/공통 컴포넌트 변경 -> DESIGN_SYSTEM, AI_UI_STYLE_GUIDE
- UI 라우트/핵심 위젯 변경 -> UI_IA, MONITORING_SCREEN_SPEC, DESIGN_SYSTEM, TEST_CASES

## 프론트엔드 원칙
- 서버 상태는 React Query, UI 상태는 Zustand
- 페이지는 얇게, 로직은 hook/service로 분리
- 차트 렌더와 데이터 변환 분리
- useEffect는 외부 시스템 동기화에만 사용
- 서버 데이터 캐시를 Zustand에 중복 저장하지 않는다

## 백엔드/엔진 원칙
- domain/application/infrastructure 분리
- Upbit raw payload를 직접 비즈니스 로직에서 사용하지 않는다
- normalize -> snapshot -> evaluate -> execute 순서를 고정한다
- 주문 시뮬레이션과 실제 주문 어댑터를 분리한다

## 실시간 꼬임 방지 규칙
- 모든 핵심 이벤트에 trace_id, event_id, dedupe key 부여
- 동일 event_id는 중복 처리 금지
- event_time / received_time / processed_time 분리
- reconnect 후 snapshot 일관성 검증
- 큐를 ingest / snapshot / evaluate 단계로 분리

## 로그 규칙
필수 로그:
- market_ingest_logs
- strategy_execution_logs
- order_simulation_logs
- risk_control_logs
- document_change_logs
- agent_action_logs
