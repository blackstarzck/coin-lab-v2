# API_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

참조:
- payload와 validation SSOT: [API_PAYLOADS.md](./API_PAYLOADS.md)
- 에러 코드와 에러 응답 형식: [ERROR_CODE_SPEC.md](./ERROR_CODE_SPEC.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

## 공통 규칙
- REST base path는 `/api/v1`
- 응답은 JSON
- 시간은 ISO 8601 UTC
- 모든 REST 응답은 `success`, `trace_id`, `timestamp`를 포함
- 에러는 `error_code` / `message` / `details` 구조를 사용
- 세션은 `strategy_version_id` 1개에 귀속되는 단일 전략 세션이다

## Strategy APIs
- POST /api/v1/strategies
- GET /api/v1/strategies
- GET /api/v1/strategies/{strategyId}
- PATCH /api/v1/strategies/{strategyId}
- POST /api/v1/strategies/{strategyId}/versions
- GET /api/v1/strategies/{strategyId}/versions
- GET /api/v1/strategy-versions/{versionId}
- POST /api/v1/strategy-versions/{versionId}/validate

## Session APIs
- POST /api/v1/sessions
- GET /api/v1/sessions
- GET /api/v1/sessions/{sessionId}
- POST /api/v1/sessions/{sessionId}/stop
- POST /api/v1/sessions/{sessionId}/kill
- GET /api/v1/sessions/{sessionId}/positions
- GET /api/v1/sessions/{sessionId}/orders
- GET /api/v1/sessions/{sessionId}/signals
- GET /api/v1/sessions/{sessionId}/risk-events
- GET /api/v1/sessions/{sessionId}/performance

## Runtime APIs
- GET /api/v1/runtime/status
- POST /api/v1/runtime/start
- POST /api/v1/runtime/stop

## Session start semantics
- fresh boot does not auto-start PAPER or LIVE sessions
- seeded/default strategies are launch candidates, not auto-running sessions
- successful POST /api/v1/sessions must start the selected mode immediately and return a RUNNING session
- LIVE start still requires explicit confirmation and live-ready configuration

## Backtest APIs
- POST /api/v1/backtests/run
- GET /api/v1/backtests
- GET /api/v1/backtests/{runId}
- GET /api/v1/backtests/{runId}/trades
- GET /api/v1/backtests/{runId}/performance
- GET /api/v1/backtests/{runId}/equity-curve
- POST /api/v1/backtests/{runId}/compare

## Monitoring APIs
- GET /api/v1/monitoring/summary

## Universe APIs
- GET /api/v1/universe/current
- POST /api/v1/universe/preview

## Metadata APIs
- GET /api/v1/metadata/indicators
- GET /api/v1/metadata/strategy-operators
- GET /api/v1/metadata/timeframes
- GET /api/v1/metadata/markets

## Log APIs
- GET /api/v1/logs/system
- GET /api/v1/logs/strategy-execution
- GET /api/v1/logs/order-simulation
- GET /api/v1/logs/risk-control
- GET /api/v1/logs/documents

## WebSocket APIs
- WS /ws/monitoring
- WS /ws/charts/{symbol}
- WS /ws/backtests/{runId}

## LIVE 보호 규칙
LIVE 시작 요청 필수:
- confirm_live=true
- acknowledge_risk=true
