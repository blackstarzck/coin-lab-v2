# 엔진 가이드

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 설계 원칙
1. Upbit 원본 메시지를 내부 표준 이벤트로 정규화한다.
2. 전략 평가는 상태 스냅샷 기반으로 수행한다.
3. 수신, 가공, 평가, 주문 시뮬레이션을 별도 모듈로 분리한다.
4. 같은 이벤트 재처리를 막기 위해 idempotency key를 사용한다.
5. BACKTEST / PAPER / LIVE는 실행 어댑터를 분리한다.

## 꼬임 방지 규칙
- UI가 전략 로직을 계산하지 않는다.
- WebSocket reconnect, order retry, DB retry 정책을 분리한다.
- 이벤트 시간(event_at), 수신 시간(received_at), 저장 시간(persisted_at)을 구분한다.
- 동일 종목/전략에 대한 중복 포지션 진입을 가드한다.
- 실패 로그에는 항상 원인 코드와 컨텍스트를 남긴다.

## 자금 관리
- 기본은 Fractional Kelly
- 최소/최대 포지션 상한 적용
- 신뢰도 부족 시 fixed-percent fallback

## 체결 모델
MVP:
- fee 반영
- slippage 반영
- 지정가 미체결 반영
- 재시도 후 시장가 전환 지원
