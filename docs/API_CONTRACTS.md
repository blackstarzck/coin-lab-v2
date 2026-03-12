# API 계약 초안

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

참조:
- 상세 엔드포인트 목록: [API_SPEC.md](./API_SPEC.md)
- request/response payload SSOT: [API_PAYLOADS.md](./API_PAYLOADS.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

## GET /api/v1/health
- 상태 확인

## GET /api/v1/strategies
- 전략 목록 조회

## POST /api/v1/strategies
- 전략 생성

## GET /api/v1/strategies/{strategyId}
- 전략 상세 조회

## POST /api/v1/backtests/run
- 백테스트 실행 요청

## GET /api/v1/monitoring/summary
- returns dashboard-ready sections: `status_bar`, `strategy_cards`, `universe_summary`, `risk_overview`, `recent_signals`
- 실시간 모니터링 요약

## 응답 규칙
- 모든 REST 응답은 `success`, `trace_id`, `timestamp`를 포함
- 에러 응답은 `error_code`, `message`, `details` 구조 사용
- 시간 필드는 ISO 8601 UTC 문자열 사용
