# 03_DETECTOR_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 구조 탐지 계층의 입출력 계약, detector 목록, 구현 우선순위, 검증 기준을 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-18
- 연계 문서:
  - [./01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
  - [./02_DOMAIN_OBJECT_SPEC.md](./02_DOMAIN_OBJECT_SPEC.md)

## 1. detector 계층의 목표
detector는 `MarketSnapshot`에서 의미 있는 구조 객체를 추출하는 계층이다.

detector는 다음을 하지 않는다.

- 바로 주문을 만들지 않는다.
- 포지션 수량을 계산하지 않는다.
- 세션 상태나 리스크 가드를 직접 판단하지 않는다.
- 전략별 score를 최종 결정하지 않는다.

detector는 다음만 한다.

- 준비 상태를 판단한다.
- 구조 객체를 생성한다.
- 탐지 근거를 `facts`와 `reason_codes`로 남긴다.

## 2. 목표 디렉토리

```text
backend/app/application/strategy_runtime/detectors/
|-- __init__.py
|-- base.py
|-- trend_context.py
|-- order_block.py
|-- fair_value_gap.py
|-- support_resistance.py
|-- structure_break.py
|-- liquidity_sweep.py
`-- retest.py
```

테스트:

```text
backend/tests/strategy_runtime/detectors/
|-- test_trend_context_detector.py
|-- test_order_block_detector.py
|-- test_fair_value_gap_detector.py
|-- test_structure_break_detector.py
|-- test_retest_detector.py
`-- fixtures/
```

## 3. detector 공통 계약

## 3.1 DetectorContext

```python
@dataclass(slots=True)
class DetectorContext:
    snapshot: MarketSnapshot
    symbol: str
    timeframe: str
    config: dict[str, object]
```

### 규칙
- detector는 필요한 config만 읽는다.
- 세션 객체나 전략 version 객체는 직접 받지 않는다.
- symbol/timeframe은 snapshot에서 유도 가능해도 명시적으로 넘긴다.

## 3.2 Detector 인터페이스

```python
class StructureDetector(Protocol):
    detector_id: str

    def required_history(self, config: dict[str, object]) -> int:
        ...

    def evaluate(self, context: DetectorContext) -> DetectorResult[MarketStructure]:
        ...
```

### 규칙
- `required_history()`는 최소 캔들 수를 반환한다.
- `evaluate()`는 반드시 `DetectorResult`를 반환한다.
- 예외를 던지기보다 `ready=false`와 `reason_codes`를 우선 사용한다.
- 코드 버그나 계약 위반만 예외로 본다.

## 3.3 DetectorResult 해석 규칙

| 상태 | 의미 |
|---|---|
| `ready=false, matched=false` | 데이터 부족 또는 평가 불가 |
| `ready=true, matched=false` | 평가했지만 구조 없음 |
| `ready=true, matched=true` | 구조 탐지 성공 |

### 공통 reason code 예시
- `DETECTOR_HISTORY_NOT_READY`
- `DETECTOR_TIMEFRAME_MISSING`
- `DETECTOR_NO_MATCH`
- `DETECTOR_MATCHED`

## 4. detector 분류

### 4.1 1차 구현 대상
- `trend_context`
- `order_block`
- `fair_value_gap`
- `structure_break`
- `retest`

### 4.2 2차 구현 대상
- `support_resistance`
- `liquidity_sweep`
- `trendline`
- `channel`

현재 코드베이스 기준으로는 1차 구현 대상이 우선이다. `smc_confluence_v1` 이관에 직접 연결되기 때문이다.

## 5. detector 상세 규격

## 5.1 trend_context detector

### 목적
- 최근 구간의 상승/하락/횡보 컨텍스트를 판단한다.

### 입력 config 예시
```json
{
  "lookback": 12,
  "minimum_history": 12
}
```

### 출력
- `TrendContext`

### 필수 facts
- `detector.trend_context.start_close`
- `detector.trend_context.latest_close`
- `detector.trend_context.average_close`
- `detector.trend_context.support`
- `detector.trend_context.resistance`

### ready 조건
- 지정 timeframe의 candle history가 `lookback` 이상 존재해야 한다.

### not_ready reason
- `DETECTOR_HISTORY_NOT_READY`
- `DETECTOR_TIMEFRAME_MISSING`

### migration source
- 현재 `smc_confluence_v1._trend_context`

## 5.2 order_block detector

### 목적
- displacement 이후 유효한 bullish/bearish order block zone을 탐지한다.

### 입력 config 예시
```json
{
  "lookback": 8,
  "body_ratio_threshold": 0.55,
  "body_pct_threshold": 0.003,
  "retest_tolerance_pct": 0.0015,
  "invalidation_buffer_pct": 0.002,
  "direction": "bullish"
}
```

### 출력
- `OrderBlockZone`

### 필수 facts
- `detector.order_block.lower`
- `detector.order_block.upper`
- `detector.order_block.invalidation_price`
- `detector.order_block.retested`
- `detector.order_block.displacement_pct`

### ready 조건
- 최소 `lookback + 3` 이상의 history가 있어야 한다.

### matched 조건
- 후보 캔들
- displacement 캔들
- follow-through
- invalidation 미발생
- 현재 시점 retest 여부 판단 가능

### migration source
- 현재 `smc_confluence_v1._detect_bullish_order_block`

## 5.3 fair_value_gap detector

### 목적
- 3캔들 기반 FVG zone을 탐지하고 retest 가능 상태를 계산한다.

### 입력 config 예시
```json
{
  "gap_threshold_pct": 0.001,
  "body_ratio_threshold": 0.55,
  "body_pct_threshold": 0.003,
  "retest_tolerance_pct": 0.0015,
  "invalidation_buffer_pct": 0.002,
  "direction": "bullish"
}
```

### 출력
- `FairValueGapZone`

### 필수 facts
- `detector.fvg.lower`
- `detector.fvg.upper`
- `detector.fvg.gap_pct`
- `detector.fvg.retested`
- `detector.fvg.invalidation_price`

### ready 조건
- 최소 4캔들 이상
- 실전 사용 기준은 detector 내부 정책으로 더 높은 history를 요구할 수 있다.

### migration source
- 현재 `smc_confluence_v1._detect_bullish_fvg`

## 5.4 structure_break detector

### 목적
- BOS/CHOCH/sweep 같은 구조 이탈을 표준화한다.

### 입력 config 예시
```json
{
  "swing_lookback": 5,
  "break_confirmation": "close",
  "break_buffer_pct": 0.0
}
```

### 출력
- `StructureBreak`

### 필수 facts
- `detector.structure_break.break_type`
- `detector.structure_break.reference_price`
- `detector.structure_break.break_price`
- `detector.structure_break.confirmed`

### 초기 범위
- 1차 구현에서는 `bos`와 `choch`까지만 우선 지원
- `sweep`는 2차 확장 가능

## 5.5 retest detector

### 목적
- zone 또는 break 이후 재시험 여부를 표준화한다.

### 입력 config 예시
```json
{
  "zone_kind": "order_block",
  "tolerance_pct": 0.0015,
  "require_rejection_candle": true
}
```

### 출력
- `RetestEvaluation`

### 입력 데이터
- snapshot
- 대상 zone 또는 structure 객체

### 필수 facts
- `detector.retest.zone_kind`
- `detector.retest.retest_price`
- `detector.retest.accepted`
- `detector.retest.rejection_confirmed`

## 6. detector 조합 규칙

### 6.1 detector 간 의존성
- `trend_context`는 독립 detector다.
- `order_block`와 `fair_value_gap`는 독립 detector다.
- `retest`는 zone detector 결과를 입력으로 받을 수 있다.
- `structure_break`는 이후 `support_resistance`나 `retest`와 같이 쓰일 수 있다.

### 6.2 composer로 넘기는 원칙
- detector는 다른 detector 결과를 직접 조합하지 않는다.
- 조합은 composer에서 수행한다.
- 다만 `retest`처럼 명백히 다른 구조 객체를 입력으로 받는 detector는 허용한다.

## 7. 구현 순서

### 7.1 1차 구현 순서
1. `base.py`
2. `trend_context.py`
3. `fair_value_gap.py`
4. `order_block.py`
5. `retest.py`
6. `structure_break.py`

### 7.2 이유
- `smc_confluence_v1` 이관에 필요한 최소 집합이다.
- FVG와 오더블록은 이미 구현된 논리를 재사용할 수 있다.
- retest는 setup 생성의 핵심이며, zone detector와 같이 검증하기 좋다.

## 8. 기존 코드베이스 영향

### 8.1 직접 영향
- `backend/app/plugins/smc_confluence_v1.py`
  - 내부 helper 함수가 detector 모듈로 빠진다.
- `backend/app/application/services/signal_generator.py`
  - detector 결과를 읽는 진입 경로가 추가된다.

### 8.2 간접 영향
- explain payload가 detector 단위 사실값을 노출하게 된다.
- fixture snapshot 요구량이 늘어나 테스트 기반이 바뀐다.

## 9. 검증 전략

## 9.1 unit 검증
각 detector는 아래 세트를 최소 포함한다.

- history 부족 시 `ready=false`
- 명확한 positive case
- 명확한 negative case
- invalidation 발생 case
- tolerance 경계값 case

## 9.2 fixture 검증
fixture는 다음 타입으로 준비한다.

- `breakout_continuation`
- `bullish_fvg_retest`
- `bullish_order_block_retest`
- `trend_context_up`
- `trend_context_range`

## 9.3 integration 검증
- `smc_confluence_v1`의 현재 결과와 detector 기반 결과를 비교한다.
- detector 결과를 explain payload로 직렬화했을 때 필요한 사실값이 누락되지 않는지 확인한다.

## 9.4 E2E 검증 기준
- 수동 또는 테스트 harness 기준으로
  - snapshot 주입
  - detector 실행
  - detector 결과 표시
  - composer 입력으로 전달
  흐름이 연결되어야 한다.

## 10. Definition of Done
- detector 모듈이 독립 파일로 존재한다.
- 1차 우선 detector에 대한 unit test가 있다.
- `smc_confluence_v1` 내부의 최소 2개 이상 helper가 detector 호출로 대체된다.
- detector facts와 reason_codes가 explain에서 재사용 가능하다.

## 11. 이번 문서의 즉시 후속 작업
- `backend/app/application/strategy_runtime/detectors/base.py` 초안 작성
- `smc_confluence_v1` 내부 helper를 detector 단위로 분해한 TODO 목록 작성
- fixture snapshot naming 규칙 확정
