# 02_DOMAIN_OBJECT_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 3층 분리 구조에서 공통으로 사용하는 도메인 객체를 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-18
- 연계 문서:
  - [./01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
  - [./03_DETECTOR_SPEC.md](./03_DETECTOR_SPEC.md)
  - [./04_EXECUTION_POLICY_SPEC.md](./04_EXECUTION_POLICY_SPEC.md)

## 1. 문서 목적
이 문서는 detector, composer, execution policy가 같은 언어로 데이터를 주고받도록 도메인 객체를 고정하기 위한 문서다.

현재 코드베이스는 다음 문제가 있다.

- detector 성격의 결과가 플러그인 내부 지역 변수로만 존재한다.
- 전략 판단에 필요한 구조 정보와 실행 정책에 필요한 가격/무효화 정보가 분리되어 있지 않다.
- explain payload에 노출되는 사실값과 실제 런타임 계산 결과가 같은 객체를 공유하지 않는다.

이 문서의 목표는 다음과 같다.

- 구조 탐지 결과를 독립된 객체로 고정한다.
- 전략 조합 결과를 setup 객체로 고정한다.
- 실행 단계에 들어갈 계획 객체를 별도로 고정한다.
- 향후 DSL, plugin, hybrid가 모두 같은 코어 객체를 사용할 수 있게 한다.

## 2. 패키지 설계

### 2.1 목표 디렉토리
```text
backend/app/domain/strategy_runtime/
|-- market_structures.py
|-- setups.py
|-- execution_plans.py
`-- decisions.py
```

### 2.2 파일 책임
- `market_structures.py`
  - detector가 만드는 구조 객체 정의
- `setups.py`
  - composer가 만드는 entry/exit setup 정의
- `execution_plans.py`
  - execution policy가 만드는 주문/포지션 계획 정의
- `decisions.py`
  - strategy draft decision, explain snapshot, orchestration 결과 정의

## 3. 계층별 객체 관계

| 계층 | 입력 | 출력 | 이 문서에서 정의하는 핵심 객체 |
|---|---|---|---|
| 분석 로직 | `MarketSnapshot` | 구조 탐지 결과 | `TrendContext`, `OrderBlockZone`, `FairValueGapZone`, `SupportResistanceZone`, `StructureBreak`, `RetestEvaluation` |
| 전략 조합 로직 | 구조 객체, 전략 설정 | setup | `EntrySetup`, `ExitSetup`, `SetupConfluence`, `RiskEnvelope` |
| 실행 로직 | setup, 세션 상태, 정책 설정 | 실행 계획 | `OrderIntentPlan`, `PositionPlan`, `ExitPlan`, `ExecutionEnvelope` |
| orchestration | decision/setup/plan | API/log/explain용 결과 | `StrategyDecisionDraft`, `ExplainSnapshot`, `ExecutionOutcomeDraft` |

## 4. 공통 설계 원칙

### 4.1 명명 규칙
- 구조 객체는 명사형으로 작성한다.
  - `OrderBlockZone`
  - `FairValueGapZone`
- 판정 결과 객체는 `Evaluation` 또는 `Result` 접미사를 사용한다.
  - `RetestEvaluation`
  - `DetectorResult`
- setup은 전략적 의도를 표현한다.
  - `EntrySetup`
  - `ExitSetup`
- plan은 실행 가능한 단계로 변환된 결과를 뜻한다.
  - `OrderIntentPlan`
  - `PositionPlan`

### 4.2 상태 규칙
- detector 결과와 setup 결과는 `ready` 여부를 가져야 한다.
- `matched`와 `ready`는 같은 의미가 아니다.
  - `ready=false`: 데이터 부족 또는 평가 불가
  - `ready=true, matched=false`: 평가 가능했지만 조건 불일치

### 4.3 explain 규칙
- 모든 핵심 객체는 explain에 사용할 `facts`, `parameters`, `reason_codes`를 동반할 수 있어야 한다.
- explain은 계산 결과를 재구성하지 않고 객체에서 직접 읽을 수 있어야 한다.

### 4.4 직렬화 규칙
- 엔티티 내부에서는 Python typed object를 사용한다.
- API payload와 저장소에는 `dict[str, object]`로 직렬화해 저장할 수 있어야 한다.
- 직렬화 가능한 스칼라만 `facts`와 `parameters`에 넣는다.

## 5. 기본 공통 객체

## 5.1 ExplainItem
설명용 공통 단위다.

```python
ExplainScalar = float | int | bool | str | None

@dataclass(slots=True, frozen=True)
class ExplainItem:
    label: str
    value: ExplainScalar
```

### 규칙
- `label`은 stable key여야 한다.
- UI 표시를 위한 localized 문자열이 아니라, 구조화된 path 성격을 유지한다.
- 예:
  - `detector.fvg.zone_low`
  - `composer.entry_setup.score`
  - `execution.entry_policy.timeout_sec`

## 5.2 DetectorResult

```python
@dataclass(slots=True)
class DetectorResult[T]:
    detector_id: str
    ready: bool
    matched: bool
    items: tuple[T, ...]
    primary: T | None
    reason_codes: tuple[str, ...]
    facts: tuple[ExplainItem, ...]
    parameters: tuple[ExplainItem, ...]
```

### 역할
- detector 결과를 표준화한다.
- 탐지 대상이 여러 개일 수 있으므로 `items`를 기본으로 둔다.
- composer는 보통 `primary` 또는 `items` 전체를 읽는다.

### 규칙
- `ready=false`면 `matched`는 `false`여야 한다.
- `primary`는 `items` 중 대표 객체여야 하며, 없으면 `None`이다.
- `reason_codes`는 준비 부족, 판정 불일치, 성공 이유를 모두 표현할 수 있다.

## 6. market_structures.py 객체 정의

## 6.1 공통 구조 객체 베이스

```python
@dataclass(slots=True)
class MarketStructure:
    structure_id: str
    kind: str
    symbol: str
    timeframe: str
    direction: str | None
    formed_at: datetime | None
    invalidated_at: datetime | None
    confidence: float | None
    facts: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

### 규칙
- `kind`는 명확한 분류값을 가진다.
  - `trend_context`
  - `order_block`
  - `fair_value_gap`
  - `support_resistance`
  - `structure_break`
  - `liquidity_sweep`
  - `retest`
- `direction`은 `bullish | bearish | neutral | None` 중 하나로 제한한다.

## 6.2 TrendContext

```python
@dataclass(slots=True)
class TrendContext(MarketStructure):
    support: float | None
    resistance: float | None
    average_close: float | None
    start_close: float | None
    latest_close: float | None
    trend_state: str
```

### 용도
- 상위 추세 필터
- invalidation reference 보조값
- confluence score 계산

### `trend_state`
- `trend_up`
- `trend_down`
- `range`
- `transition`

## 6.3 PriceZone

```python
@dataclass(slots=True)
class PriceZone(MarketStructure):
    lower: float
    upper: float
    midpoint: float
    invalidation_price: float | None
    retested: bool
    active: bool
```

### 역할
- zone 성격 구조의 공통 필드
- `OrderBlockZone`, `FairValueGapZone`, `SupportResistanceZone`의 베이스 역할

## 6.4 OrderBlockZone

```python
@dataclass(slots=True)
class OrderBlockZone(PriceZone):
    source_candle_at: datetime | None
    impulse_candle_at: datetime | None
    body_ratio: float | None
    displacement_pct: float | None
```

## 6.5 FairValueGapZone

```python
@dataclass(slots=True)
class FairValueGapZone(PriceZone):
    left_candle_at: datetime | None
    middle_candle_at: datetime | None
    right_candle_at: datetime | None
    gap_pct: float | None
```

## 6.6 SupportResistanceZone

```python
@dataclass(slots=True)
class SupportResistanceZone(PriceZone):
    touch_count: int
    source: str
```

### `source`
- `swing_high_low`
- `trendline_projection`
- `channel_boundary`
- `manual_level`

## 6.7 StructureBreak

```python
@dataclass(slots=True)
class StructureBreak(MarketStructure):
    break_type: str
    reference_price: float | None
    break_price: float | None
    confirmed: bool
```

### `break_type`
- `bos`
- `choch`
- `sweep`

## 6.8 RetestEvaluation

```python
@dataclass(slots=True)
class RetestEvaluation(MarketStructure):
    zone_kind: str
    zone_lower: float | None
    zone_upper: float | None
    retest_price: float | None
    accepted: bool
    rejection_confirmed: bool
```

### 역할
- zone 재시험 여부를 표준화한다.
- setup 생성 시 직접 활용된다.

## 7. setups.py 객체 정의

## 7.1 SetupConfluence

```python
@dataclass(slots=True)
class SetupConfluence:
    score: int
    max_score: int
    matched_conditions: tuple[str, ...]
    failed_conditions: tuple[str, ...]
    facts: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

## 7.2 RiskEnvelope

```python
@dataclass(slots=True)
class RiskEnvelope:
    invalidation_price: float | None
    stop_loss_price: float | None
    take_profit_prices: tuple[float, ...]
    trailing_activation_price: float | None
    max_holding_bars: int | None
```

### 역할
- setup 단계에서 계산 가능한 risk 기준을 모아 둔다.
- execution policy는 이 값을 해석해 주문 계획으로 변환한다.

## 7.3 EntrySetup

```python
@dataclass(slots=True)
class EntrySetup:
    setup_id: str
    symbol: str
    timeframe: str
    direction: str
    setup_type: str
    valid: bool
    confidence: float | None
    trigger_price: float | None
    preferred_entry_zone: tuple[float, float] | None
    invalidation_price: float | None
    confluence: SetupConfluence
    risk: RiskEnvelope
    structures: tuple[MarketStructure, ...]
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

### `setup_type` 예시
- `fvg_retest_long`
- `order_block_retest_long`
- `trendline_bounce_long`
- `breakout_continuation_long`

## 7.4 ExitSetup

```python
@dataclass(slots=True)
class ExitSetup:
    setup_id: str
    symbol: str
    timeframe: str
    exit_type: str
    valid: bool
    priority: int
    trigger_price: float | None
    invalidation_price: float | None
    structures: tuple[MarketStructure, ...]
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

### `exit_type` 예시
- `zone_invalidation`
- `trailing_stop`
- `take_profit`
- `time_stop`
- `strategy_discretionary_exit`

## 7.5 StrategyDecisionDraft

```python
@dataclass(slots=True)
class StrategyDecisionDraft:
    action: str
    confidence: float | None
    entry_setup: EntrySetup | None
    exit_setup: ExitSetup | None
    matched_conditions: tuple[str, ...]
    failed_conditions: tuple[str, ...]
    facts: tuple[ExplainItem, ...]
    parameters: tuple[ExplainItem, ...]
    reason_codes: tuple[str, ...]
```

### 역할
- composer 결과의 최종 요약
- 아직 주문 의도는 만들지 않은 상태

## 8. execution_plans.py 객체 정의

## 8.1 OrderIntentPlan

```python
@dataclass(slots=True)
class OrderIntentPlan:
    symbol: str
    side: str
    order_role: str
    order_type: str
    requested_qty: float
    requested_price: float | None
    timeout_sec: float | None
    fallback_to_market: bool
    retries_allowed: int
    reason_codes: tuple[str, ...] = ()
    facts: tuple[ExplainItem, ...] = ()
```

## 8.2 PositionPlan

```python
@dataclass(slots=True)
class PositionPlan:
    size_mode: str
    notional_krw: float | None
    expected_qty: float
    initial_stop_loss: float | None
    initial_take_profit: float | None
    partial_take_profits: tuple[tuple[float, float], ...]
    trailing_stop_pct: float | None
```

### `partial_take_profits`
- `(target_price, close_ratio)` 쌍을 저장한다.

## 8.3 ExitPlan

```python
@dataclass(slots=True)
class ExitPlan:
    exit_type: str
    order_type: str
    trigger_price: float | None
    close_ratio: float
    priority: int
    fallback_to_market: bool
    reason_codes: tuple[str, ...] = ()
```

## 8.4 ExecutionEnvelope

```python
@dataclass(slots=True)
class ExecutionEnvelope:
    entry_intent: OrderIntentPlan | None
    position_plan: PositionPlan | None
    exit_plans: tuple[ExitPlan, ...]
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

### 역할
- execution policy 계층의 최종 산출물
- `ExecutionService`가 주문/포지션 상태 갱신을 할 때 읽는 표준 입력

## 9. decisions.py 객체 정의

## 9.1 ExplainSnapshot

```python
@dataclass(slots=True)
class ExplainSnapshot:
    snapshot_key: str
    decision: str
    detector_facts: tuple[ExplainItem, ...]
    setup_facts: tuple[ExplainItem, ...]
    execution_facts: tuple[ExplainItem, ...]
    parameters: tuple[ExplainItem, ...]
    matched_conditions: tuple[str, ...]
    failed_conditions: tuple[str, ...]
    reason_codes: tuple[str, ...]
    risk_blocks: tuple[str, ...]
```

### 역할
- 현재 `ExplainPayload`의 상위 버전 개념
- detector/composer/execution 계층 사실값을 구분해서 유지한다.

## 9.2 ExecutionOutcomeDraft

```python
@dataclass(slots=True)
class ExecutionOutcomeDraft:
    accepted: bool
    order_intent: OrderIntentPlan | None
    fill_price: float | None
    fill_qty: float
    resulting_position_state: str | None
    explain_snapshot: ExplainSnapshot | None
    reason_codes: tuple[str, ...]
```

## 10. 기존 코드와의 매핑

| 현재 위치 | 현재 역할 | 목표 객체 |
|---|---|---|
| `smc_confluence_v1._trend_context` | 추세 계산 | `TrendContext` |
| `smc_confluence_v1._detect_bullish_order_block` | 오더블록 탐지 | `OrderBlockZone` |
| `smc_confluence_v1._detect_bullish_fvg` | FVG 탐지 | `FairValueGapZone` |
| `SignalGenerator.build_plugin_explain_payload` | explain payload 조합 | `ExplainSnapshot` |
| `ExecutionService._create_order_intent` | 주문 의도 생성 | `OrderIntentPlan` |
| `ExecutionService._calculate_position_size` | 포지션 계획 일부 | `PositionPlan` |
| `FillEngine.evaluate_exit_triggers` | 청산 정책 일부 | `ExitPlan` |

## 11. 구현 우선순위

### 11.1 먼저 만들 객체
- `ExplainItem`
- `DetectorResult`
- `TrendContext`
- `OrderBlockZone`
- `FairValueGapZone`
- `EntrySetup`
- `StrategyDecisionDraft`
- `OrderIntentPlan`
- `PositionPlan`
- `ExplainSnapshot`

### 11.2 나중에 추가할 객체
- `SupportResistanceZone`
- `StructureBreak`
- `RetestEvaluation`
- `ExitSetup`
- `ExitPlan`
- `ExecutionOutcomeDraft`

## 12. 검증 기준

### 12.1 코드 검증
- 객체 생성 테스트
- `asdict` 또는 serializer 테스트
- `facts`, `parameters`, `reason_codes`가 빈 상태에서도 안전한지 확인

### 12.2 구조 검증
- detector 결과가 composer 입력으로 손실 없이 이동 가능한지 확인
- composer 결과가 execution policy 입력으로 손실 없이 이동 가능한지 확인
- explain payload 생성에 필요한 필드가 빠지지 않았는지 확인

### 12.3 이관 검증
- `smc_confluence_v1`가 새 객체만으로 필요한 정보를 모두 표현할 수 있어야 한다.
- 기존 `ExplainPayload`와 호환 가능한 최소 매핑이 가능해야 한다.

## 13. 이번 문서의 즉시 후속 작업
- [./03_DETECTOR_SPEC.md](./03_DETECTOR_SPEC.md) 기준으로 detector contract 정의
- fixture snapshot을 이용한 첫 객체 샘플 생성
- `smc_confluence_v1` 내부 함수별 반환값을 새 객체로 매핑하는 spike 작성
