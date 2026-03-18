# 04_EXECUTION_POLICY_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 실행 정책 계층의 모듈 경계, 정책 계약, 기존 필드와의 매핑, 검증 기준을 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-18
- 연계 문서:
  - [./01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
  - [./02_DOMAIN_OBJECT_SPEC.md](./02_DOMAIN_OBJECT_SPEC.md)

## 1. 실행 정책 계층의 목표
실행 정책 계층은 전략 판단 결과를 실제 주문 의도와 포지션 관리 계획으로 바꾸는 계층이다.

현재 코드베이스의 문제는 다음과 같다.

- `ExecutionService`가 전략과 실행 사이의 책임을 동시에 가진다.
- `FillEngine`이 체결 시뮬레이션, trailing stop, partial TP 계산을 함께 처리한다.
- 일부 설정은 validator에만 있고 실제 실행에는 연결되지 않는다.
  - `exit_order_type`
  - `max_order_retries`
  - `partial_take_profits`

이 문서의 목표는 다음과 같다.

- 전략의 판단과 실행 방법을 분리한다.
- 실행 정책을 작은 모듈로 나눈다.
- 기존 strategy config 필드를 명확한 policy 모듈에 매핑한다.
- BACKTEST/PAPER/LIVE가 같은 코어를 재사용할 수 있는 실행 계약을 만든다.

## 2. 목표 디렉토리

```text
backend/app/application/strategy_runtime/execution/
|-- __init__.py
|-- base.py
|-- entry_policy.py
|-- exit_policy.py
|-- sizing_policy.py
|-- order_lifecycle.py
|-- fill_simulator.py
|-- exit_trigger_evaluator.py
`-- risk_gate_adapter.py
```

테스트:

```text
backend/tests/strategy_runtime/execution/
|-- test_entry_policy.py
|-- test_exit_policy.py
|-- test_sizing_policy.py
|-- test_order_lifecycle.py
|-- test_fill_simulator.py
`-- test_execution_envelope.py
```

## 3. 계층 경계

| 계층 | 책임 | 하지 말아야 할 일 |
|---|---|---|
| detector | 구조 탐지 | 주문 판단 |
| composer | setup 생성 | 실제 주문 수량 계산 |
| execution policy | 주문/포지션 계획 생성 | raw market structure 직접 탐지 |
| orchestration service | 세션/리스크/저장소 연결 | 계산 세부 구현 보유 |

### 핵심 원칙
- 전략은 `왜 진입하는가`를 말한다.
- execution policy는 `어떻게 진입하는가`를 말한다.

## 4. 실행 정책 공통 계약

## 4.1 ExecutionContext

```python
@dataclass(slots=True)
class ExecutionContext:
    session: Session
    strategy_config: dict[str, object]
    snapshot: MarketSnapshot
    decision: StrategyDecisionDraft
    entry_setup: EntrySetup | None
    exit_setup: ExitSetup | None
```

## 4.2 Policy 인터페이스

```python
class EntryPolicy(Protocol):
    policy_id: str
    def build_order_intent(self, context: ExecutionContext) -> OrderIntentPlan | None: ...

class ExitPolicy(Protocol):
    policy_id: str
    def build_exit_plans(self, context: ExecutionContext, position: Position | None) -> tuple[ExitPlan, ...]: ...

class SizingPolicy(Protocol):
    policy_id: str
    def build_position_plan(self, context: ExecutionContext, order_intent: OrderIntentPlan | None) -> PositionPlan | None: ...

class FillSimulator(Protocol):
    simulator_id: str
    def simulate(self, intent: OrderIntentPlan, context: ExecutionContext) -> FillResult: ...
```

### 규칙
- 각 policy는 자기 역할 외 계산을 하지 않는다.
- policy 입력은 `ExecutionContext`와 typed plan object를 사용한다.
- `ExecutionService`는 policy 조합 결과를 저장소와 상태 갱신에 연결하는 orchestration만 담당한다.

## 5. 정책 분해 기준

## 5.1 entry policy

### 책임
- 주문 타입 결정
- 요청 가격 계산
- timeout/fallback/retry 정책 결정
- order role 결정

### 초기 구현 후보
- `market_entry_policy`
- `limit_entry_policy`
- `limit_then_market_entry_policy`
- `zone_retest_limit_entry_policy`

### 기존 필드 매핑
| 기존 필드 | 정책 영향 |
|---|---|
| `execution.entry_order_type` | 시장가/지정가 진입 정책 선택 |
| `execution.limit_timeout_sec` | 지정가 timeout |
| `execution.fallback_to_market` | 지정가 미체결 후 시장가 전환 여부 |
| `risk.max_order_retries` | 주문 재시도 허용치 |

## 5.2 sizing policy

### 책임
- 포지션 수량/명목금액 계산
- 사이징 캡 적용
- 전략 초기 stop을 고려한 risk-per-trade 계산

### 초기 구현 후보
- `fixed_amount_sizing_policy`
- `fixed_percent_sizing_policy`
- `fractional_kelly_sizing_policy`
- `risk_per_trade_sizing_policy`

### 기존 필드 매핑
| 기존 필드 | 정책 영향 |
|---|---|
| `position.size_mode` | 사이징 정책 선택 |
| `position.size_value` | 정책 파라미터 |
| `position.size_caps` | min/max cap |
| `backtest.initial_capital` | percent/kelly/risk 계산 기준 |

### 주의
- 현재 코드에는 `fixed_qty` 경로가 테스트용으로 남아 있다.
- 버전업 과정에서 `fixed_qty`는 테스트 전용 fallback인지 정식 schema인지 정리해야 한다.

## 5.3 exit policy

### 책임
- 청산 우선순위 구성
- stop/take-profit/trailing/zone invalidation/time-stop를 `ExitPlan`으로 변환
- partial take profit 계획 생성

### 초기 구현 후보
- `hard_stop_exit_policy`
- `take_profit_exit_policy`
- `partial_take_profit_exit_policy`
- `trailing_stop_exit_policy`
- `zone_invalidation_exit_policy`
- `time_stop_exit_policy`
- `strategy_discretionary_exit_policy`

### 기존 필드 매핑
| 기존 필드 | 정책 영향 |
|---|---|
| `exit.stop_loss_pct` | hard stop 정책 |
| `exit.take_profit_pct` | take profit 정책 |
| `exit.partial_take_profits` | partial TP 계획 |
| `exit.trailing_stop_pct` | trailing stop 정책 |
| `exit.time_stop_bars` | time stop 정책 |
| `execution.exit_order_type` | 시장가/지정가 청산 방식 |

## 5.4 order lifecycle policy

### 책임
- 생성, 제출, 대기, 부분 체결, timeout, 취소, fallback의 상태 흐름 관리
- 재시도 여부와 종료 조건 결정

### 초기 구현 후보
- `simple_order_lifecycle`
- `limit_timeout_then_market_lifecycle`

### 기존 필드 매핑
| 기존 필드 | 정책 영향 |
|---|---|
| `execution.limit_timeout_sec` | timeout 규칙 |
| `execution.fallback_to_market` | fallback 경로 |
| `risk.max_order_retries` | retry count |

## 5.5 fill simulator

### 책임
- 모드에 맞는 fill price 추정
- fee/slippage 적용
- partial fill 계산

### 초기 구현 후보
- `market_fill_simulator`
- `limit_fill_simulator`
- `backtest_fill_simulator`
- `paper_fill_simulator`

### 기존 필드 매핑
| 기존 필드 | 정책 영향 |
|---|---|
| `backtest.fill_assumption` | base fill price 산정 |
| `execution.slippage_model` | slippage 적용 방식 |
| `backtest.slippage_bps` | slippage 수치 |
| `execution.fee_model` | fee 계산 모델 |
| `backtest.fee_bps` | fee 수치 |

## 6. 기존 코드와의 분해 계획

| 현재 위치 | 현재 책임 | 목표 모듈 |
|---|---|---|
| `ExecutionService._create_order_intent` | entry intent 생성 | `entry_policy.py` |
| `ExecutionService._calculate_position_size` | 사이징 | `sizing_policy.py` |
| `ExecutionService._simulate_fill` | fill 시뮬레이션 | `fill_simulator.py` |
| `ExecutionService._handle_limit_timeout` | lifecycle 일부 | `order_lifecycle.py` |
| `FillEngine.evaluate_exit_triggers` | 청산 판정 | `exit_trigger_evaluator.py` |
| `FillEngine.process_partial_take_profits` | partial TP | `exit_policy.py` 또는 `partial_exit_policy.py` |

## 7. 정책 조합 예시

## 7.1 FVG 리테스트 long
- composer 출력
  - `EntrySetup(setup_type="fvg_retest_long", preferred_entry_zone=(zone_low, zone_high), invalidation_price=zone_low_buffered)`
- execution 조합
  - entry policy: `zone_retest_limit_entry_policy`
  - sizing policy: `fixed_percent_sizing_policy`
  - exit policy:
    - `hard_stop_exit_policy`
    - `partial_take_profit_exit_policy`
    - `trailing_stop_exit_policy`
    - `zone_invalidation_exit_policy`

## 7.2 breakout continuation
- composer 출력
  - `EntrySetup(setup_type="breakout_continuation_long", trigger_price=breakout_level)`
- execution 조합
  - entry policy: `market_entry_policy`
  - sizing policy: `fixed_amount_sizing_policy`
  - exit policy:
    - `hard_stop_exit_policy`
    - `take_profit_exit_policy`

## 8. 정책 선택 방식

### 8.1 단기 방안
- 기존 config field를 읽어 내부에서 policy를 선택한다.
- 예:
  - `size_mode == fixed_percent` -> `FixedPercentSizingPolicy`
  - `entry_order_type == limit and fallback_to_market == true` -> `LimitThenMarketEntryPolicy`

### 8.2 장기 방안
- hybrid/module catalog에서 policy id를 명시적으로 저장한다.
- 예:
```json
{
  "execution_modules": {
    "entry_policy": "limit_then_market_entry",
    "sizing_policy": "fixed_percent",
    "exit_policies": ["hard_stop", "partial_take_profit", "zone_invalidation"]
  }
}
```

## 9. 검증되지 않은 필드 연결 우선순위

### 우선 연결 대상
- `exit_order_type`
- `partial_take_profits`
- `max_order_retries`

### 이유
- 현재 문서와 validator에는 존재하지만 실행 경로 반영이 약하다.
- 이 필드들이 실제 policy로 연결되어야 config와 runtime의 신뢰성이 올라간다.

## 10. 테스트 전략

## 10.1 unit 테스트
- entry policy:
  - 시장가 진입
  - 지정가 진입
  - zone 기반 limit price 생성
- sizing policy:
  - fixed amount
  - fixed percent
  - size cap 적용
- exit policy:
  - stop loss
  - take profit
  - partial take profit
  - trailing stop
  - invalidation exit
- lifecycle:
  - timeout
  - fallback
  - retry exhaustion
- fill simulator:
  - fee 반영
  - slippage 반영
  - limit fill success/failure

## 10.2 integration 테스트
- `ExecutionService`가 policy 조합을 호출하는지 검증
- signal -> order intent -> fill -> position update의 전체 체인 검증
- 기존 explain payload와 새 execution facts를 함께 출력할 수 있는지 확인

## 10.3 E2E 검증 기준
- BACKTEST/PAPER 공통 기준
  - entry setup이 유효하면 order intent가 생성되어야 한다.
  - fill이 발생하면 position state가 갱신되어야 한다.
  - exit plan이 발동하면 적절한 우선순위대로 청산되어야 한다.
  - logs와 explain에 execution facts가 남아야 한다.

## 11. Definition of Done
- `ExecutionService`의 주요 세부 계산이 policy 계층으로 분리된다.
- `partial_take_profits`가 실행 경로에 반영된다.
- `exit_order_type`가 실제 plan 또는 order intent에 반영된다.
- `max_order_retries`가 lifecycle policy에 반영된다.
- 관련 unit/integration 테스트가 추가된다.

## 12. 구현 시 주의사항
- 정책 분리 중에도 기존 API contract는 가능한 유지한다.
- `Session`, `Order`, `Position` 엔티티는 당장 크게 바꾸지 않는다.
- `NETWORK_FLOW_PLAYBOOK` 업데이트가 필요한 수준의 런타임 흐름 변경이 생기면 같은 작업에서 문서를 갱신한다.

## 13. 이번 문서의 즉시 후속 작업
- `ExecutionService` 책임 분해 TODO 작성
- `FillEngine`의 함수별 소속 정책 매핑 작성
- `partial_take_profits`, `exit_order_type`, `max_order_retries`의 현재 미연결 경로 확인용 테스트 추가
