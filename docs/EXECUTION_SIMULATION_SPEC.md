# EXECUTION_SIMULATION_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 BACKTEST / PAPER / LIVE 모드의 실행 및 체결 규칙을 정의한다.  
수익률, 승률, MDD가 모드별로 과도하게 달라지지 않도록 공통 규칙을 고정한다.

참조:
- 상태 enum SSOT: [STATE_MACHINE.md](./STATE_MACHINE.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

---

## 2. 핵심 원칙
- 전략 평가는 모드와 무관하게 동일 snapshot 입력을 사용한다
- 리스크 차단은 주문 생성보다 우선한다
- 체결 시뮬레이션은 낙관적 해석보다 보수적 해석을 우선한다
- 같은 signal이라도 mode에 따라 adapter는 다르지만 state machine은 최대한 공유한다
- LIVE는 거래소 응답을 source of truth로 삼고, BACKTEST/PAPER는 내부 체결 엔진을 source of truth로 삼는다

---

## 3. 실행 모드 정의

## 3.1 BACKTEST
- 과거 데이터 replay
- 실제 주문 없음
- historical candle/trade data 기반
- 지정가 미체결/재시도/시장가 fallback을 문서 규칙대로 시뮬레이션

## 3.2 PAPER
- 실시간 데이터 기반
- 실제 주문 없음
- 현재 시장 조건으로 체결 추정
- 지정가 timeout, fallback 규칙 적용

## 3.3 LIVE
- 실시간 데이터 기반
- 실제 거래소 주문
- 거래소 응답과 fill event가 source of truth
- 내부 계산은 보조 판단용

---

## 4. 공통 체결 단계
1. signal 생성
2. risk check
3. order intent 생성
4. adapter 변환
5. submit
6. pending/open fill wait
7. fill / partial fill / timeout / cancel
8. fallback 또는 종료
9. position state 갱신
10. 로그 및 성과 기록

---

## 5. 주문 타입

### market
특징:
- 즉시 체결 가정
- BACKTEST/PAPER에서는 slippage 반영
- LIVE에서는 거래소 응답 가격을 사용

### limit
특징:
- 지정가 제출
- timeout 동안 체결 대기
- 미체결 시 cancel 또는 fallback_to_market 가능

---

## 6. 수수료 모델

### 기본값
- `fee_model = per_fill`
- `fee_bps`: strategy.backtest 또는 session config에서 제공
- fee = executed_notional * fee_bps / 10000

### 규칙
- partial fill은 fill마다 fee 계산
- 백테스트도 fill 단위로 누적 fee 계산
- 반올림 규칙은 decimal precision 문서를 따른다
- 수수료 없는 테스트는 명시적으로 `fee_bps=0`

---

## 7. 슬리피지 모델

### 7.1 none
- 슬리피지 0

### 7.2 fixed_bps
- buy fill price = base_price * (1 + bps/10000)
- sell fill price = base_price * (1 - bps/10000)

### 7.3 volatility_scaled
예시:
- effective_bps = base_bps * max(1.0, recent_volatility_ratio)

### 적용 시점
- market order는 항상 적용 가능
- limit order는 실제 체결 가격이 limit보다 불리해지는 슬리피지는 원칙적으로 적용하지 않음
- 단, fallback_to_market이 발생한 경우 market 규칙 적용

---

## 8. 가격 기준

## 8.1 BACKTEST
기본값:
- `fill_assumption = next_bar_open`

허용:
- `next_bar_open`
- `mid`
- `next_tick`
- `best_bid_ask`

규칙:
- candle-only 데이터일 때 `next_tick`, `best_bid_ask`는 사용 불가
- 지정가 주문은 다음 순서로 평가:
  1. 주문 제출 시점 기준 target limit price 생성
  2. 이후 candle/trade path에서 해당 가격 도달 여부 확인
  3. timeout 내 미도달 시 미체결 처리

## 8.2 PAPER
- 실시간 trade stream 또는 synthetic best price 기준
- 마지막 거래가만 있으면 보수적으로 불리한 방향 가격 사용 가능

## 8.3 LIVE
- 거래소 fill event 우선
- 내부 추정 가격은 UI preview 용도

---

## 9. limit timeout / fallback 규칙

### 공통 필드
- `limit_timeout_sec`
- `fallback_to_market`
- `max_order_retries`

### 동작
1. limit 주문 제출
2. timeout 내 완전 체결되면 종료
3. partial fill이면 남은 수량 기준 다음 정책 적용
4. timeout 시:
   - `fallback_to_market=true` → cancel 후 market 재주문
   - `fallback_to_market=false` → order cancelled

### 권장 기본값
- entry limit timeout: 15초
- exit limit timeout: 10초
- 재시도 횟수: 2회

---

## 10. partial fill 규칙
- partial fill은 허용
- position quantity는 체결량 기준으로 증가/감소
- partial exit 시 remaining qty에 대해 stop/take-profit 다시 계산
- timeout 후 남은 물량만 fallback 처리 가능
- partial fill이 한 번이라도 발생하면 order state는 `PARTIALLY_FILLED` 이력을 남긴다

---

## 11. 진입 규칙

### 11.1 진입 전 체크
- session 상태가 `RUNNING`
- symbol별 max_open_positions 미초과
- duplicate entry 아님
- daily loss limit 미도달
- strategy kill switch 미작동
- max concurrent positions 미초과

### 11.2 진입 가격
#### market entry
- BACKTEST: `base_price + slippage`
- PAPER: `best_estimated_fill + slippage`
- LIVE: actual exchange fill

#### limit entry
- 전략 또는 execution policy에 따라 지정가 결정
- 기본값: signal 시점의 reference price 기준 불리하지 않은 가격 사용
  - buy: best bid 또는 reference close 이하
  - sell: best ask 또는 reference close 이상

---

## 12. 청산 규칙

### 12.1 청산 트리거 우선순위
동일 시점에 복수 청산 트리거가 맞으면 우선순위는 아래와 같다.

1. 강제 kill / emergency stop
2. 거래소 reject 후 안전 청산
3. stop loss
4. trailing stop
5. take profit
6. time stop
7. manual stop
8. strategy discretionary exit

### 12.2 같은 candle 안에서 stop/take 동시 도달
보수적 원칙:
- LONG 포지션은 stop loss 우선
- SHORT가 없다면 현물 기준 sell exit만 있으므로 stop을 우선 적용
- 명시적으로 다른 `intra_bar_priority`를 지정하지 않으면 보수적 규칙 사용

---

## 13. 부분 익절 규칙
```json
[
  { "at_profit_pct": 0.02, "close_ratio": 0.5 },
  { "at_profit_pct": 0.04, "close_ratio": 0.25 }
]
```

### 규칙
- 낮은 수익 목표부터 오름차순 정렬
- 동일 가격대 중복 금지
- `close_ratio` 합계는 1 이하
- partial TP 후 stop을 breakeven 이상으로 옮기는 추가 정책은 별도 risk/execution 옵션으로 분리

---

## 14. trailing stop 규칙
- trailing anchor는 체결 후 최고가(high-watermark)
- trailing stop price = high_watermark * (1 - trailing_stop_pct)
- partial take profit 후에도 remaining position 기준 유지
- trailing stop은 stop loss보다 높은 가격이 되면 effective stop으로 대체 가능

---

## 15. 재시도 규칙

### retryable 대상
- submit timeout
- temporary network failure
- cancel timeout
- transient db persist failure

### non-retryable 대상
- validation failure
- insufficient balance
- risk block
- duplicate entry
- invalid price increment

### 정책
- exponential backoff + jitter
- max retries 초과 시 risk event 기록
- LIVE에서 submit 결과 미확실하면 **중복 주문 방지 우선**
  - 거래소 order 조회
  - idempotency key 조회
  - 확인 전 재주문 금지

---

## 16. 상태 전이

### OrderState
- `CREATED`
- `SUBMITTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELLED`
- `REJECTED`
- `EXPIRED`
- `FAILED`

### PositionState
- `NONE`
- `OPENING`
- `OPEN`
- `CLOSING`
- `CLOSED`
- `FAILED`

보조 규칙:
- partial close는 별도 `PositionState`가 아니라 주문 이력과 remaining quantity로 표현한다
- risk block은 position state가 아니라 signal / risk event 레벨에서 기록한다

---

## 17. 성과 계산
- realized pnl = Σ(sell proceeds) - Σ(buy cost) - Σ(fees)
- unrealized pnl = mark_to_market(current_price) - position cost basis - projected exit fee
- pnl_pct는 invested capital 대비
- partial fill/partial exit 포함 시 weighted average entry/exit 사용

---

## 18. mode별 차이 요약

| 항목 | BACKTEST | PAPER | LIVE |
|---|---|---|---|
| 데이터 | 과거 replay | 실시간 | 실시간 |
| 체결 source | 내부 엔진 | 내부 엔진 | 거래소 fill |
| 주문 제출 | 없음 | 없음 | 실제 제출 |
| 미체결 처리 | 시뮬레이션 | 시뮬레이션 | 거래소 상태 조회 |
| 슬리피지 | 모델 기반 | 모델 기반 | 실제 fill 반영 |
| 수수료 | 모델 기반 | 모델 기반/예상 | 실제 수수료 우선 |

---

## 19. 예시 시나리오

### 시나리오 A: limit entry 미체결 후 market fallback
1. 10:00:00 ENTER signal
2. buy limit 100원 제출
3. 10:00:15 timeout
4. cancel 성공
5. buy market 재주문
6. 101원 fill
7. order history에 limit-cancel + market-fill 모두 기록

### 시나리오 B: 같은 봉에서 TP와 SL 모두 닿음
- 기본 규칙에 따라 stop loss 우선
- 결과적으로 exit reason = `STOP_LOSS_INTRA_BAR_CONSERVATIVE`

### 시나리오 C: partial fill 후 timeout
- 총 1.0 수량 중 0.4 체결
- timeout 후 remaining 0.6만 market fallback
- average entry price는 두 체결 가격의 가중 평균
