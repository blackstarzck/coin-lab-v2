# EVENT_FLOW.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 상위 흐름
1. Upbit WebSocket 수신
2. Raw payload 검증
3. Normalized Event 변환
4. Market State 업데이트
5. Candidate Universe 갱신
6. Snapshot 생성
7. Strategy Evaluate
8. Signal 생성
9. Risk Guard 검사
10. Order Intent 생성
11. Execution Adapter 처리
12. Position/Session 업데이트
13. 로그/저장/UI 전파

## 이벤트 종류
### Raw
- raw_trade
- raw_ticker
- raw_orderbook

### Normalized
- TradeTickEvent
- TickerEvent
- OrderBookEvent
- CandleClosedEvent
- UniverseChangedEvent
- StrategyEvaluatedEvent
- SignalCreatedEvent
- RiskBlockedEvent
- OrderIntentCreatedEvent
- ExecutionUpdatedEvent
- SessionStateChangedEvent

## 시간 필드
- event_time_utc
- received_time_utc
- processed_time_utc

## Dedupe 규칙
중복 방지 key 예:
- source + symbol + trade_id
- source + symbol + sequence
- source + symbol + event_time + price + volume

## Candidate Universe 흐름
1. base market list
2. 거래대금 집계
3. 급등/급락/거래량 급증 탐지
4. watchlist 병합
5. 중복 제거
6. 전략 호환성 필터
7. max_symbols 절단

## Snapshot 생성 트리거
- CandleClosedEvent
- 일정 주기 trade batch flush
- UniverseChangedEvent
- SessionControlEvent

## Risk Guard 순서
1. session active 여부
2. mode 허용 여부
3. duplicate entry 차단
4. max open positions
5. daily loss limit
6. strategy drawdown limit
7. kill switch
8. symbol cooldown / reentry reset

## 재연결 흐름
1. disconnect 감지
2. reconnect backoff
3. connection restored
4. gap recovery 또는 fresh snapshot rebuild
5. state consistency check
6. resume
