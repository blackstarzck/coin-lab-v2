# TEST_STRATEGY.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 테스트 피라미드
1. Unit Tests
2. Frontend Component/Hook Tests
3. Integration Tests
4. Simulation/Replay Tests
5. Regression Tests
6. Performance/Load Tests

## 1. Unit Tests
대상:
- indicator calculators
- DSL parser/validator
- strategy decision engine
- Kelly sizing calculator
- fee/slippage calculator
- dedupe key generator
- risk guards
- state transition helpers
- JSON <-> form mapper

## 2. Frontend Tests
대상:
- StrategyForm hooks
- Monitoring panel selectors
- Compare table
- Risk badge components
- Log filters
- Chart marker mapper

## 3. Integration Tests
시나리오:
- 전략 저장 후 새 버전 생성
- 세션 시작 후 RUNNING 진입
- 신호 생성 후 리스크 차단
- 백테스트 완료 후 metrics/trades 저장
- 로그 조회 필터 정상 동작

## 4. Replay Tests
필수 시나리오:
- 같은 trade event 중복 수신
- 늦게 도착한 tick이 이전 candle window에 속함
- disconnect 후 재연결
- 고속 tick burst
- entry 후 즉시 duplicate signal
- stop loss와 take profit 동시 후보 edge case

## 5. Regression Tests
golden metrics:
- total return
- max drawdown
- win rate
- profit factor
- trade count
- avg holding time

## 6. Performance Tests
대상:
- top 10 dynamic universe + 4 strategies 동시 실행
- websocket burst 처리
- 실시간 차트 갱신
- 장기 백테스트 실행

## 7. LIVE 보호 테스트
- confirm_live required
- kill switch 동작
- daily loss limit 차단
- 재시도 횟수 제한
- idempotency key 중복 방지
