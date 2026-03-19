# 01_LAYERED_EXECUTION_UPGRADE_PLAN.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 생성과 실행 코어를 3층 분리 구조로 버전업하기 위한 실제 개발 실행 계획을 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-18
- 연계 문서:
  - [../ENGINE_GUIDELINES.md](../ENGINE_GUIDELINES.md)
  - [../EXECUTION_SIMULATION_SPEC.md](../EXECUTION_SIMULATION_SPEC.md)
  - [../STRATEGY_DSL_SPEC.md](../STRATEGY_DSL_SPEC.md)
  - [../NETWORK_FLOW_PLAYBOOK.md](../NETWORK_FLOW_PLAYBOOK.md)

## 1. 문서 사용 범위
이 문서는 다음 작업을 시작하기 전의 기준 문서다.

- 전략 파라미터를 단순 추가하는 대신, 로직 단위를 모듈화하는 작업
- `StrategyRuntimeEvaluator`, `SignalGenerator`, `ExecutionService`, `FillEngine`의 책임 재분배
- SMC/가격 구조 기반 전략을 재사용 가능한 조합형 구조로 전환하는 작업
- `dsl`, `plugin`, `hybrid` 전략 타입을 장기적으로 정리하는 작업
- 백테스트, PAPER 실행, LIVE 실행이 공통 코어를 공유하도록 기반을 재구성하는 작업

이 문서는 구현 개요가 아니라 실제 착수 기준이다. 각 단계는 범위, 선행 작업, 영향도, 검증 기준까지 포함한다.

## 2. 문제 정의

### 2.1 현재 구조의 장점
- 전략 진입 조건을 DSL로 표현할 수 있다.
- `plugin` 전략을 등록하고 런타임에서 호출할 수 있다.
- `ExecutionService`와 `FillEngine`이 시장가/지정가 시뮬레이션의 최소 동작을 제공한다.
- `smc_confluence_v1` 같은 복합 전략의 초기 버전이 존재한다.

### 2.2 현재 구조의 한계
- 파라미터와 로직 단위가 분리되지 않아, 전략이 늘수록 플러그인 내부 로직이 비대해질 가능성이 크다.
- `StrategyRuntimeEvaluator`는 비교형 leaf에는 적합하지만, 구조 객체 생성이 필요한 전략에는 표현력이 낮다.
- `ExecutionService`가 신호 해석, 주문 의도 생성, 체결 처리, 포지션 갱신, 일부 exit explain까지 함께 담당한다.
- `FillEngine`에 체결 시뮬레이션과 exit trigger 판정이 섞여 있다.
- `BacktestService`와 `workers/*`가 아직 placeholder 성격이 강해, 고도화된 전략의 재현성 검증에 적합하지 않다.
- `hybrid` 타입이 UI에서 비활성화되어 있어, 장기 확장 경로가 문서와 코드에서 완전히 정렬되지 않았다.

### 2.3 해결 방향
전략 코어를 다음 3층으로 분리한다.

1. 분석 로직
   캔들/틱/스냅샷으로부터 구조 객체를 생성한다.
2. 전략 조합 로직
   구조 객체와 지표/가격 상태를 조합해 진입/청산 setup을 만든다.
3. 실행 로직
   setup을 실제 주문 의도와 포지션 관리 정책으로 변환한다.

핵심 원칙은 다음과 같다.

- 파라미터는 독립된 설정 뭉치가 아니라, 반드시 소속된 로직 단위를 가져야 한다.
- 전략은 “무엇을 발견했는가”와 “그래서 무엇을 할 것인가”를 분리해야 한다.
- 실행은 “왜 진입/청산하는가”가 아니라 “어떻게 체결하고 관리하는가”를 책임져야 한다.
- 한 번 계산한 구조 객체는 explain, backtest, monitoring, plugin 재사용에 공통으로 쓰여야 한다.

## 3. 목표 아키텍처

### 3.1 3층 분리 목표

#### A. 분석 로직
- 입력: `MarketSnapshot`
- 출력: 구조 객체와 관찰 결과
- 예시:
  - `TrendContext`
  - `OrderBlockZone`
  - `FairValueGapZone`
  - `SupportResistanceZone`
  - `BreakOfStructure`
  - `LiquiditySweep`
  - `RetestResult`

#### B. 전략 조합 로직
- 입력: 분석 로직의 결과, 전략 설정
- 출력: `EntrySetup`, `ExitSetup`, `StrategyDecisionDraft`
- 예시:
  - FVG 리테스트 + 상위 추세 상승 + 확인 캔들
  - 오더블록 유지 + BOS 이후 되돌림 진입
  - 추세선 반등 + 거래량 확장 + 무효화 가격 설정

#### C. 실행 로직
- 입력: setup, 세션 상태, 리스크 상태, 실행 정책
- 출력: `OrderIntent`, `PositionPlan`, `ExitPlan`, `ExecutionResult`
- 예시:
  - 지정가 진입 후 timeout 시 시장가 전환
  - 부분익절 후 stop을 breakeven으로 상향
  - zone invalidation 시 전량 청산

### 3.2 최종 목표 구조
기존 서비스 진입점은 유지하되, 내부 로직은 점진적으로 아래 구조로 이동한다.

```text
backend/app/
|-- application/
|   |-- services/
|   |   |-- execution_service.py          # orchestration only
|   |   |-- signal_generator.py           # orchestration only
|   |   |-- runtime_service.py            # orchestration only
|   |   `-- backtest_service.py           # orchestration only
|   `-- strategy_runtime/
|       |-- detectors/
|       |   |-- trend_context.py
|       |   |-- order_block.py
|       |   |-- fair_value_gap.py
|       |   |-- support_resistance.py
|       |   |-- structure_break.py
|       |   `-- retest.py
|       |-- composers/
|       |   |-- entry_setups/
|       |   |-- exit_setups/
|       |   `-- confluence.py
|       |-- execution/
|       |   |-- entry_policy.py
|       |   |-- exit_policy.py
|       |   |-- sizing_policy.py
|       |   |-- order_lifecycle.py
|       |   |-- fill_simulator.py
|       |   `-- risk_gate_adapter.py
|       |-- explain/
|       |   `-- explain_builder.py
|       `-- mappers/
|           |-- dsl_mapper.py
|           `-- plugin_mapper.py
|-- domain/
|   |-- entities/                         # existing session/order/position 유지
|   `-- strategy_runtime/
|       |-- market_structures.py
|       |-- setups.py
|       |-- execution_plans.py
|       `-- decisions.py
|-- plugins/
|   |-- breakout_v1.py                    # thin wrapper
|   `-- smc_confluence_v1.py              # thin wrapper
`-- tests/
    |-- strategy_runtime/
    |   |-- detectors/
    |   |-- composers/
    |   |-- execution/
    |   `-- fixtures/
    `-- e2e/
        |-- test_strategy_to_execution_flow.py
        `-- test_backtest_reproducibility.py
```

### 3.3 디렉토리 변경 원칙
- 기존 public entrypoint 파일은 즉시 삭제하지 않는다.
- 1차 이관은 새 패키지를 추가하고 기존 서비스가 새 모듈을 호출하도록 만든다.
- 플러그인은 thin wrapper로 축소한다.
- 테스트는 서비스 테스트만 유지하지 않고 detector/composer/policy 단위 테스트로 세분화한다.

## 4. 현재 코드베이스 영향 분석

### 4.1 직접 영향이 큰 파일
- `backend/app/application/services/strategy_runtime_evaluator.py`
  - 비교형 DSL evaluator 중심에서 “기본형 leaf evaluator”로 역할이 축소될 가능성이 높다.
- `backend/app/application/services/signal_generator.py`
  - signal 생성 단일 책임으로 축소하고, detector/composer 호출 orchestration을 맡게 된다.
- `backend/app/application/services/execution_service.py`
  - 주문 의도 생성, 체결 실행, 포지션 갱신, explain 일부를 직접 처리하는 구조를 분해해야 한다.
- `backend/app/application/services/fill_engine.py`
  - `fill_simulator`, `exit_trigger_evaluator`, `partial_exit_manager` 성격으로 분리될 수 있다.
- `backend/app/plugins/smc_confluence_v1.py`
  - detector 재사용 기반 composer 플러그인 혹은 hybrid mapper로 이관 후보이다.
- `backend/app/application/services/backtest_service.py`
  - placeholder 성격의 결과를 제거하고 공통 코어 replay 호출부로 변경해야 한다.
- `workers/backtest.py`, `workers/strategy_runtime.py`
  - placeholder에서 실제 orchestration worker로 전환해야 한다.

### 4.2 간접 영향이 큰 파일
- `backend/app/application/services/strategy_validator.py`
  - detector/composer/policy 기반 설정 검증 규칙이 추가된다.
- `backend/app/domain/entities/session.py`
  - 기존 엔티티 유지 가능성이 높지만, setup/plan/result용 새 객체가 추가될 수 있다.
- `frontend/src/entities/strategy/dsl-types.ts`
  - hybrid type 및 세분화된 execution policy/strategy module 구성이 반영된다.
- `frontend/src/features/strategies/pluginCatalog.ts`
  - 플러그인별 개별 파라미터 화면에서 “전략 모듈 조합형” 화면으로 전환될 수 있다.
- `frontend/src/pages/StrategyEditPage.tsx`
  - 현재 disabled된 hybrid 경로를 장기적으로 활성화해야 한다.
- `docs/STRATEGY_DSL_SPEC.md`
  - detector/composer/policy 개념이 반영되면 SSOT 수정이 필요하다.
- `docs/EXECUTION_SIMULATION_SPEC.md`
  - 실행 정책 모듈 단위로 재정리해야 한다.
- `docs/NETWORK_FLOW_PLAYBOOK.md`
  - 런타임 평가 흐름이나 실행 ownership이 바뀌면 반드시 검토가 필요하다.

### 4.3 리스크
- 서비스 파일을 한 번에 이동하면 회귀 범위가 너무 커진다.
- detector가 늘어나면 snapshot history 요구량이 커져 런타임 비용과 데이터 준비 조건이 바뀔 수 있다.
- 전략 explain payload 구조가 바뀌면 monitoring UI에도 영향이 생긴다.
- execution policy 세분화 과정에서 현재 테스트가 놓치던 회귀가 드러날 수 있다.

## 5. 개발 방식

### 5.1 권장 이행 전략
- Big-bang refactor 금지
- Additive migration 우선
- 서비스 entrypoint 유지
- 단계별 feature flag 또는 strategy-level opt-in 유지
- 기존 전략과 새 구조 전략을 일정 기간 병행 지원

### 5.2 구현 순서 원칙
- 도메인 객체 정의 없이 detector 구현부터 시작하지 않는다.
- detector 없이 composer를 만들지 않는다.
- setup 없이 execution policy를 만들지 않는다.
- backtest 고도화 전에 공통 execution core 계약을 먼저 고정한다.

### 5.3 문서 동기화 원칙
다음 단계는 구현과 같은 task에서 문서 갱신을 동반해야 한다.

- 4단계 실행 정책 분리
- 5단계 hybrid 도입
- 6단계 테스트/재현성 구조 확정
- 7단계 기존 전략 이관

## 6. 7단계 실행 계획

## 단계 1. 공통 개념과 도메인 객체 표준화

### 목적
- detector, composer, execution policy가 공통으로 사용하는 데이터 모델을 고정한다.
- 파라미터가 로직 단위에 종속되는 구조를 문서와 코드 양쪽에서 정의한다.

### 범위
- `MarketStructure`, `EntrySetup`, `ExitSetup`, `ExecutionPlan`, `DecisionContext` 정의
- 구조 객체의 최소 속성 정의
- explain payload에 구조 객체 요약이 들어갈 수 있도록 기준 정의

### 선행 작업
- 현재 `smc_confluence_v1`, `StrategyRuntimeEvaluator`, `FillEngine`, `ExecutionService`에서 쓰는 필드를 수집한다.
- 현재 UI가 읽는 explain payload 구조를 정리한다.

### 후속 작업
- 단계 2 detector 계층 구현
- 단계 3 composer 계층 구현

### 디렉토리 변경
- 추가:
  - `backend/app/domain/strategy_runtime/`
  - `backend/tests/strategy_runtime/fixtures/`

### 개발 방식
- 새 도메인 객체를 dataclass 또는 pydantic model로 정의한다.
- 기존 서비스는 당장 새 객체를 전부 쓰지 않아도 되지만, 새 객체 import가 가능하도록 추가한다.
- detector/composer 구현 전, fixture snapshot과 기대 구조 객체 샘플을 함께 만든다.

### 코드베이스 영향
- 기존 서비스 동작 변경은 최소화한다.
- 새 도메인 객체만 추가하는 단계이므로 회귀 위험은 낮다.
- 다만 이후 단계의 기준 계약이 되므로 naming과 field semantics를 여기서 신중히 고정해야 한다.

### 완료 기준
- 구조 객체/strategy setup/execution plan의 초안이 코드와 문서 모두 존재한다.
- fixture snapshot으로 구조 객체 예시를 만들 수 있다.
- explain payload와 연결될 필드 명명 규칙이 정의되어 있다.

### 자체 검증
- unit:
  - 객체 생성 테스트
  - 직렬화/역직렬화 테스트
  - fixture snapshot compatibility 테스트
- 문서:
  - 구조 객체 표와 필드 설명 확인
- 수동:
  - `smc_confluence_v1`에서 필요한 데이터가 모두 매핑 가능한지 확인

### E2E 검증 기준
- 없음
- 이 단계는 런타임 E2E보다 계약 고정이 핵심이다.

## 단계 2. detector 계층 분리

### 목적
- 구조 탐지 로직을 플러그인/서비스에서 떼어내 재사용 가능한 분석 계층으로 만든다.

### 범위
- 우선순위 detector:
  - `trend_context`
  - `order_block`
  - `fair_value_gap`
  - `retest`
  - `structure_break`
- 입력: `MarketSnapshot`
- 출력: 단계 1에서 정의한 구조 객체

### 선행 작업
- 단계 1 완료
- detector별 최소 history 요구량 정의
- snapshot fixture 정리

### 후속 작업
- 단계 3 composer 조합
- 단계 7 SMC 플러그인 이관

### 디렉토리 변경
- 추가:
  - `backend/app/application/strategy_runtime/detectors/`
  - `backend/tests/strategy_runtime/detectors/`

### 개발 방식
- detector는 side effect 없이 pure function 또는 stateless service로 구현한다.
- detector는 signal을 반환하지 않는다.
- 각 detector는 `ready / not_ready`, `reason_codes`, `facts`를 포함한 결과를 반환한다.
- 첫 구현은 `smc_confluence_v1`의 내부 로직을 그대로 옮기되, API를 범용화한다.

### 코드베이스 영향
- `smc_confluence_v1` 내부 함수가 detector로 이동된다.
- `StrategyRuntimeEvaluator`의 역할과 detector의 역할이 충돌하지 않도록 선을 그어야 한다.
- detector가 늘면 CPU 사용량과 snapshot history 요구량이 커질 수 있다.

### 완료 기준
- 최소 3개 이상의 detector가 독립 모듈로 분리된다.
- `smc_confluence_v1` 내부의 FVG/오더블록 계산이 detector를 사용하도록 전환된다.
- detector 단위 테스트가 fixture 기반으로 존재한다.

### 자체 검증
- unit:
  - 상승 FVG 탐지
  - 상승 오더블록 탐지
  - 리테스트 판정
  - history 부족 시 `not_ready`
- integration:
  - 기존 `smc_confluence_v1` 결과와 detector 결과 비교
- 성능:
  - 동일 snapshot 반복 평가 시 허용 가능한 실행 시간 측정

### E2E 검증 기준
- 수동 런타임 검증:
  - 샘플 snapshot을 넣었을 때 detector 결과가 explain/debug 경로로 조회 가능해야 한다.

## 단계 3. 전략 조합 계층 도입

### 목적
- detector 결과를 조합해 reusable setup을 만드는 계층을 도입한다.

### 범위
- `EntrySetupComposer`
- `ExitSetupComposer`
- `ConfluenceScorer`
- `StrategyDecisionDraftBuilder`

### 선행 작업
- 단계 2 detector 완료
- setup 객체와 explain 포맷 확정

### 후속 작업
- 단계 4 execution policy 분리
- 단계 7 전략 이관

### 디렉토리 변경
- 추가:
  - `backend/app/application/strategy_runtime/composers/`
  - `backend/tests/strategy_runtime/composers/`

### 개발 방식
- composer는 detector 결과를 받아 setup을 만든다.
- composer는 주문 타입, 수량 계산, fallback 정책을 결정하지 않는다.
- composer는 최소한 다음을 반환한다.
  - setup 유효 여부
  - setup type
  - invalidation price
  - confidence 또는 score
  - matched conditions
  - failed conditions

### 코드베이스 영향
- `SignalGenerator`는 직접 전략 조건을 해석하는 대신 composer 호출 orchestration으로 단순화된다.
- `smc_confluence_v1`는 detector + composer를 호출하는 thin wrapper로 전환 가능하다.
- explain payload 생성 책임 일부가 composer/ explain builder로 이동한다.

### 완료 기준
- `smc_confluence_v1`와 유사한 confluence 전략이 composer 기반으로 동작한다.
- composer 출력이 signal 생성 전 단계의 표준 형태로 고정된다.
- explain payload가 detector 사실과 composer 판단을 분리해 보여줄 수 있다.

### 자체 검증
- unit:
  - detector 결과 조합으로 entry setup 생성
  - invalidation price 계산
  - score threshold 판정
- integration:
  - `SignalGenerator`가 composer 결과를 사용해 진입 신호를 만들 수 있는지 확인

### E2E 검증 기준
- 전략 explain 응답에서
  - detector facts
  - composer matched conditions
  - setup invalidation
  - reason_codes
  가 일관되게 노출되어야 한다.

## 단계 4. 실행 정책 계층 분리

### 목적
- 전략 판단과 실행 방법을 완전히 분리한다.

### 범위
- `EntryPolicy`
- `ExitPolicy`
- `SizingPolicy`
- `OrderLifecyclePolicy`
- `FillSimulator`
- `ExitTriggerEvaluator`

### 선행 작업
- 단계 3 setup 출력 고정
- 현재 `ExecutionService`와 `FillEngine` 책임 분해 목록 정리

### 후속 작업
- 단계 5 hybrid 표현 반영
- 단계 6 재현성 테스트

### 디렉토리 변경
- 추가:
  - `backend/app/application/strategy_runtime/execution/`
  - `backend/tests/strategy_runtime/execution/`

### 개발 방식
- `ExecutionService`는 orchestration layer로 유지하고 세부 정책은 하위 모듈로 위임한다.
- 정책 단위 예시:
  - `fixed_percent_sizing`
  - `fixed_amount_sizing`
  - `limit_then_market_entry`
  - `market_immediate_exit`
  - `partial_take_profit_policy`
  - `zone_invalidation_exit_policy`
- 현재 미사용 또는 부분 구현 상태인 옵션을 실제 정책으로 연결한다.
  - `exit_order_type`
  - `partial_take_profits`
  - `max_order_retries`
  - `trailing_stop_pct`

### 코드베이스 영향
- `ExecutionService`가 크게 줄어든다.
- `FillEngine`는 분리 또는 rename 대상이다.
- `BacktestService`는 나중에 이 execution core를 사용하도록 연결할 수 있다.
- 네트워크/세션/심볼 흐름에 간접 영향이 생길 수 있으므로 구현 시 [../NETWORK_FLOW_PLAYBOOK.md](../NETWORK_FLOW_PLAYBOOK.md) 검토가 필요하다.

### 완료 기준
- `ExecutionService`가 직접 계산하던 sizing/fill/exit 일부가 정책 모듈로 이동한다.
- `partial_take_profits`가 실제 실행 경로에 연결된다.
- `exit_order_type`가 실행에 반영된다.
- `max_order_retries`가 적어도 시뮬레이션/intent 레벨에서 의미를 가진다.

### 자체 검증
- unit:
  - 시장가 진입
  - 지정가 미체결 후 fallback
  - 부분익절
  - trailing stop
  - invalidation exit
- integration:
  - `ExecutionService`가 policy 조합을 호출하는지 검증

### E2E 검증 기준
- PAPER/BACKTEST 공통 흐름에서
  - signal 생성
  - order intent 생성
  - fill 처리
  - position 업데이트
  - explain/log 기록
  이 한 흐름으로 연결되어야 한다.

## 단계 5. hybrid 전략 표현 정리

### 목적
- detector/composer/policy 조합을 UI와 저장 스키마에 반영해, 전략 정의를 모듈 조합형으로 전환한다.

### 범위
- `hybrid` 전략 타입 활성화 준비
- DSL과 plugin의 경계 재정리
- `dsl-types.ts`, validator, editor UI 갱신

### 선행 작업
- 단계 3, 단계 4 완료
- 어떤 모듈을 DSL로 표현하고 어떤 모듈을 plugin으로 남길지 결정

### 후속 작업
- 단계 7 기존 전략 이관

### 디렉토리 변경
- 추가 가능:
  - `backend/app/application/strategy_runtime/mappers/`
  - `frontend/src/features/strategies/moduleCatalog.ts`

### 개발 방식
- 초기 hybrid는 완전 자유 조합보다 제한된 catalog 조합으로 시작한다.
- 예시:
  - detector set
  - confluence rule
  - entry policy
  - exit policy
  - sizing policy
- UI는 무제한 form이 아니라 “조합 가능한 모듈 카탈로그” 기반으로 설계한다.

### 코드베이스 영향
- validator가 단순 필드 유무 검사에서 모듈 조합 검증으로 확장된다.
- `StrategyEditPage.tsx`가 가장 큰 변경 영향을 받는다.
- `pluginCatalog.ts`는 장기적으로 `moduleCatalog.ts` 성격으로 이동 가능하다.

### 완료 기준
- 최소 1개 이상의 hybrid 전략을 UI/백엔드에서 생성/저장/검증할 수 있다.
- 현재 disabled 상태인 hybrid가 제한된 범위에서 활성화된다.
- 저장된 config가 detector/composer/policy 조합을 표현할 수 있다.

### 자체 검증
- unit:
  - hybrid config validation
  - module compatibility validation
- integration:
  - strategy create/update/validate API
  - UI draft validation

### E2E 검증 기준
- 전략 편집 페이지에서 hybrid 전략 생성
- validation 통과
- 세션 실행
- monitoring explain에서 setup 및 policy 정보 확인

## 단계 6. 재현성과 테스트 체계 강화

### 목적
- 고도화된 구조가 같은 입력에 같은 결과를 내는지 보장한다.
- detector/composer/execution 계층 각각의 회귀를 빠르게 찾을 수 있게 한다.

### 범위
- fixture 기반 snapshot 세트 구축
- detector/composer/policy/E2E 테스트 분리
- backtest reproducibility 기준 수립
- explain/log snapshot golden test 도입

### 선행 작업
- 단계 2~5 중 최소 detector/composer/execution policy 경로 확보

### 후속 작업
- 단계 7 대규모 이관

### 디렉토리 변경
- 추가:
  - `backend/tests/e2e/`
  - `backend/tests/golden/`

### 개발 방식
- fixture snapshot은 전략 예시별로 분리한다.
  - breakout
  - FVG retest
  - order block hold
  - trendline bounce
- explain payload와 execution log는 golden 비교 대상으로 둔다.
- backtest는 같은 입력 데이터와 설정으로 같은 trade list가 나와야 한다.

### 코드베이스 영향
- 테스트 수가 많이 늘어난다.
- 개발 속도는 일시적으로 느려질 수 있지만, 이후 구조 변경 비용을 크게 줄인다.
- placeholder 상태인 backtest worker/service를 실제 검증 경로에 연결할 준비가 된다.

### 완료 기준
- detector/composer/execution 각각 독립 테스트가 있다.
- 최소 2개 전략 시나리오에 대한 end-to-end 테스트가 있다.
- 같은 fixture 재실행 시 결과가 변하지 않는다.

### 자체 검증
- unit:
  - detector/composer/policy 전체
- integration:
  - runtime service + execution service + repository
- regression:
  - golden explain payload
  - golden execution logs

### E2E 검증 기준
- `strategy config -> snapshot -> decision -> execution -> logs -> explain` 전체 체인이 재현 가능해야 한다.
- 동일 fixture 3회 반복 실행 결과가 동일해야 한다.

## 단계 7. 기존 전략과 서비스의 점진적 이관

### 목적
- 새 구조를 실제 운영 경로에 연결하고, 기존 전략들을 단계적으로 전환한다.

### 범위
- `smc_confluence_v1` 이관
- `breakout_v1` 이관
- `SignalGenerator`, `ExecutionService`, `BacktestService` 점진 이관
- placeholder worker 교체

### 선행 작업
- 단계 2~6의 핵심 경로 완료

### 후속 작업
- 운영 모니터링 보강
- 문서 SSOT 정식 갱신

### 디렉토리 변경
- 없음
- 이 단계는 추가보다는 기존 서비스 내부 호출 경로 전환이 중심이다.

### 개발 방식
- 한 전략씩 이관한다.
- 전략별 이관 순서:
  1. detector 교체
  2. composer 교체
  3. execution policy 연결
  4. explain payload 비교
  5. 기존 경로 제거 여부 판단
- worker는 placeholder를 제거하고 실제 orchestration으로 교체한다.

### 코드베이스 영향
- 회귀 위험이 가장 높다.
- monitoring explain과 log 구조가 바뀔 수 있다.
- UI가 기존 필드명을 직접 기대하고 있으면 조정이 필요하다.

### 완료 기준
- `smc_confluence_v1`이 새 구조 위에서 동작한다.
- `breakout_v1`도 같은 코어를 공유한다.
- `BacktestService`가 placeholder metrics 대신 실제 실행 코어 결과를 반환한다.
- `workers/backtest.py`, `workers/strategy_runtime.py`가 placeholder가 아니다.

### 자체 검증
- unit:
  - 기존 전략 래퍼 동작
- integration:
  - 세션 생성부터 실행까지 기존 API 호환성 확인
- 수동:
  - 전략별 explain payload 비교
  - 로그 event type 확인

### E2E 검증 기준
- 전략 생성 또는 버전 선택
- 세션 실행
- 신호 생성
- 주문 처리
- 포지션 변화
- 청산
- monitoring/logs/backtests 화면에서 결과 확인

## 7. 단계 간 의존성 요약

| 단계 | 선행 단계 | 핵심 산출물 | 다음 단계 영향 |
|---|---|---|---|
| 1 | 없음 | 도메인 객체 계약 | 2, 3, 4의 기준 |
| 2 | 1 | detector 계층 | 3, 7 |
| 3 | 2 | setup/composer 계층 | 4, 5, 7 |
| 4 | 3 | execution policy 계층 | 5, 6, 7 |
| 5 | 3, 4 | hybrid 표현과 UI/validator | 7 |
| 6 | 2, 3, 4, 5 일부 | 재현성 테스트 체계 | 7 안정성 확보 |
| 7 | 2~6 | 실제 운영 경로 이관 | 정식 버전업 완료 |

## 8. 구현 우선순위 추천

### 1차 마일스톤
- 단계 1
- 단계 2 일부
- 단계 3 일부

목표:
- `smc_confluence_v1`를 재사용 가능한 detector/composer 구조로 분해할 수 있는 기반 확보

### 2차 마일스톤
- 단계 4
- 단계 6 일부

목표:
- execution policy 연결과 테스트 체계 구축

### 3차 마일스톤
- 단계 5
- 단계 7

목표:
- hybrid 표현 도입과 실제 운영 경로 이관

## 9. 착수 전 체크리스트
- [ ] 단계 1에서 정의할 도메인 객체 명명 규칙 초안이 있는가
- [ ] `smc_confluence_v1` 내부 로직을 detector 단위로 분해한 목록이 있는가
- [ ] `ExecutionService`와 `FillEngine`의 책임 분해안이 정리되어 있는가
- [ ] explain payload 필수 필드가 정리되어 있는가
- [ ] UI가 기대하는 strategy config shape가 정리되어 있는가
- [ ] 단계 4 이후 네트워크 흐름 변경 시 [../NETWORK_FLOW_PLAYBOOK.md](../NETWORK_FLOW_PLAYBOOK.md) 갱신 여부를 확인할 담당 범위가 정해졌는가

## 10. 이번 문서 작성 시점의 권고 결론
- 지금 바로 해야 할 일은 새 엔진을 여러 개 만드는 것이 아니다.
- 먼저 구조 탐지, 전략 조합, 실행 정책을 분리하는 공통 코어를 세우는 것이 맞다.
- 첫 이관 대상은 `smc_confluence_v1`이 가장 적절하다.
- 현재 코드베이스에서는 `additive migration + thin wrapper 전략`이 가장 안전하다.
