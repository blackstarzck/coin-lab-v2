# 05_MIGRATION_CHECKLIST.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 3층 분리 구조로의 이관 작업을 단계별 체크리스트와 위험 관리 기준으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-18
- 연계 문서:
  - [./01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
  - [./02_DOMAIN_OBJECT_SPEC.md](./02_DOMAIN_OBJECT_SPEC.md)
  - [./03_DETECTOR_SPEC.md](./03_DETECTOR_SPEC.md)
  - [./04_EXECUTION_POLICY_SPEC.md](./04_EXECUTION_POLICY_SPEC.md)

## 1. 문서 사용 방식
이 문서는 실제 구현 PR 또는 작업 단위를 쪼갤 때 사용하는 체크리스트다.

- 계획 문서는 방향과 범위를 설명한다.
- 이 문서는 작업 순서, 완료 기준, 회귀 확인 지점을 정리한다.

## 2. 공통 이행 원칙
- 한 번에 전체 구조를 갈아엎지 않는다.
- 기존 서비스 entrypoint는 당분간 유지한다.
- 새 모듈 추가 후 호출 경로만 점진적으로 전환한다.
- detector/composer/policy 이관이 끝나기 전에는 플러그인 thin wrapper를 유지한다.
- 설명 payload와 로그 이벤트 타입이 바뀌면 UI 영향도를 함께 확인한다.

## 3. 작업 전 공통 체크
- [ ] 현재 변경 대상 파일과 신규 파일을 확정했다.
- [ ] 이번 작업이 `NETWORK_FLOW_PLAYBOOK` 갱신 대상인지 판단했다.
- [ ] 기존 테스트 중 보호해야 하는 시나리오를 적었다.
- [ ] 이번 작업에서 임시 호환 코드가 필요한지 판단했다.
- [ ] 기존 config shape와 새 config shape의 호환 범위를 정했다.

## 4. 단계별 체크리스트

## 단계 1. 도메인 객체 표준화

### 착수 전
- [ ] `backend/app/domain/strategy_runtime/` 디렉토리 생성
- [ ] 최소 객체 목록 확정
  - [ ] `ExplainItem`
  - [ ] `DetectorResult`
  - [ ] `TrendContext`
  - [ ] `OrderBlockZone`
  - [ ] `FairValueGapZone`
  - [ ] `EntrySetup`
  - [ ] `OrderIntentPlan`
  - [ ] `PositionPlan`
  - [ ] `ExplainSnapshot`

### 구현 중
- [ ] 객체별 필드명과 타입을 코드로 선언
- [ ] 직렬화 helper 또는 serializer 방향 결정
- [ ] explain payload와 연결되는 필드명 규칙 반영

### 완료 전
- [ ] 객체 생성 테스트 작성
- [ ] fixture snapshot과 매핑 가능한지 확인
- [ ] 기존 `smc_confluence_v1`에서 필요한 정보가 모두 표현되는지 확인

## 단계 2. detector 분리

### 착수 전
- [ ] detector base contract 작성
- [ ] fixture snapshot 세트 준비
- [ ] `smc_confluence_v1` helper 함수 분해 목록 작성

### 구현 중
- [ ] `trend_context` detector 추가
- [ ] `fair_value_gap` detector 추가
- [ ] `order_block` detector 추가
- [ ] `retest` detector 추가
- [ ] `structure_break` detector 추가 여부 판단

### 완료 전
- [ ] 각 detector unit test 작성
- [ ] `ready=false` 시나리오 테스트 포함
- [ ] `smc_confluence_v1` 내부 최소 2개 helper를 detector 호출로 교체

## 단계 3. composer 분리

### 착수 전
- [ ] `EntrySetup`과 `ExitSetup` 필드가 고정되었는지 확인
- [ ] detector 결과를 어떤 composer가 소비할지 목록화

### 구현 중
- [ ] confluence score builder 작성
- [ ] entry setup composer 작성
- [ ] exit setup composer 작성
- [ ] strategy decision draft builder 작성

### 완료 전
- [ ] detector facts와 composer facts가 분리되어 explain 가능한지 확인
- [ ] `SignalGenerator`가 composer 결과를 받아 signal을 만들 수 있는지 확인
- [ ] `smc_confluence_v1` thin wrapper 전환 가능성 검토

## 단계 4. execution policy 분리

### 착수 전
- [ ] `ExecutionService` 책임 분해 목록 고정
- [ ] `FillEngine` 함수별 소속 정책 매핑 고정
- [ ] 현재 미사용 필드 목록 재확인
  - [ ] `exit_order_type`
  - [ ] `partial_take_profits`
  - [ ] `max_order_retries`

### 구현 중
- [ ] entry policy 구현
- [ ] sizing policy 구현
- [ ] exit policy 구현
- [ ] order lifecycle policy 구현
- [ ] fill simulator 구현

### 완료 전
- [ ] 시장가/지정가 진입 테스트
- [ ] timeout/fallback 테스트
- [ ] partial take profit 테스트
- [ ] trailing stop 테스트
- [ ] invalidation exit 테스트

## 단계 5. hybrid 표현 이관

### 착수 전
- [ ] UI에서 hybrid를 어떤 수준까지 허용할지 결정
- [ ] validator 확장 범위 결정
- [ ] module catalog 초안 작성

### 구현 중
- [ ] backend mapper 작성
- [ ] frontend module catalog 작성
- [ ] `StrategyEditPage` 입력 구조 조정
- [ ] validation API 대응

### 완료 전
- [ ] hybrid 전략 draft 생성 가능
- [ ] validate 가능
- [ ] 저장 가능
- [ ] 세션에서 실행 가능

## 단계 6. 재현성/테스트 체계 강화

### 착수 전
- [ ] fixture naming 규칙 고정
- [ ] golden test 범위 고정
- [ ] E2E 대표 전략 2종 이상 선택

### 구현 중
- [ ] detector fixture 구축
- [ ] composer fixture 구축
- [ ] execution regression fixture 구축
- [ ] explain golden test 작성
- [ ] execution log golden test 작성

### 완료 전
- [ ] 동일 fixture 3회 반복 실행 결과 동일
- [ ] E2E 2종 이상 통과
- [ ] flaky test 여부 점검

## 단계 7. 기존 전략/서비스 이관

### 착수 전
- [ ] `smc_confluence_v1` 이관 순서 고정
- [ ] `breakout_v1` 이관 순서 고정
- [ ] `BacktestService` placeholder 제거 계획 고정
- [ ] worker placeholder 제거 계획 고정

### 구현 중
- [ ] `smc_confluence_v1` thin wrapper 전환
- [ ] `breakout_v1` thin wrapper 전환
- [ ] `SignalGenerator` orchestration 단순화
- [ ] `ExecutionService` orchestration 단순화
- [ ] `BacktestService` 실제 코어 연결
- [ ] `workers/backtest.py` 구현
- [ ] `workers/strategy_runtime.py` 구현

### 완료 전
- [ ] monitoring explain 회귀 확인
- [ ] strategy execution log 회귀 확인
- [ ] backtest 결과 placeholder 제거 확인

## 5. 파일 단위 migration map

| 현재 파일 | 작업 유형 | 목표 상태 |
|---|---|---|
| `backend/app/plugins/smc_confluence_v1.py` | shrink | detector/composer 호출 wrapper |
| `backend/app/plugins/breakout_v1.py` | shrink | composer/entry policy 호출 wrapper |
| `backend/app/application/services/strategy_runtime_evaluator.py` | split or narrow | DSL leaf evaluator 중심 |
| `backend/app/application/services/signal_generator.py` | narrow | orchestration only |
| `backend/app/application/services/execution_service.py` | narrow | orchestration only |
| `backend/app/application/services/fill_engine.py` | split | fill simulator + exit evaluator |
| `backend/app/application/services/backtest_service.py` | replace internals | 실제 공통 실행 코어 연결 |
| `workers/backtest.py` | replace placeholder | 실제 백테스트 orchestration |
| `workers/strategy_runtime.py` | replace placeholder | 실제 런타임 orchestration |
| `frontend/src/features/strategies/pluginCatalog.ts` | extend or migrate | module/hybrid catalog 반영 |
| `frontend/src/pages/StrategyEditPage.tsx` | refactor | hybrid/module 조합 UI 반영 |

## 6. PR 분리 권장안

### PR 1
- 도메인 객체 추가
- fixture 초안 추가
- 문서 업데이트

### PR 2
- detector 1차 세트 추가
- detector unit test 추가
- `smc_confluence_v1` 일부 이관

### PR 3
- composer 추가
- signal generator 일부 이관
- explain payload 정리

### PR 4
- execution policy 추가
- `ExecutionService`/`FillEngine` 분해
- integration test 추가

### PR 5
- hybrid 표현 추가
- UI/validator 연동

### PR 6
- reproducibility/golden/E2E 테스트 추가

### PR 7
- 기존 전략 이관 완료
- placeholder worker 제거
- backtest 실제 코어 연결

## 7. 회귀 위험 체크리스트

### 전략 판단
- [ ] 기존 breakout 전략 진입/비진입 기준이 변하지 않았는가
- [ ] `smc_confluence_v1`의 주요 진입 구간이 크게 달라지지 않았는가

### 실행
- [ ] 시장가 진입 fill price가 기존 대비 의도치 않게 바뀌지 않았는가
- [ ] 지정가 미체결 후 fallback 동작이 유지되는가
- [ ] stop/take-profit 우선순위가 문서와 일치하는가

### UI
- [ ] explain panel이 필요한 필드를 모두 표시하는가
- [ ] 전략 편집 페이지가 기존 strategy type도 문제없이 열리는가
- [ ] hybrid 비활성 상태에서 기존 사용자 흐름이 깨지지 않는가

### 네트워크/런타임
- [ ] 세션 선택 흐름이 바뀌지 않았는가
- [ ] active symbol 차트 websocket 흐름이 깨지지 않았는가
- [ ] monitoring summary websocket과 충돌하지 않는가

## 8. 단계 완료 후 검증 템플릿

각 단계 종료 시 아래 항목을 기록한다.

### 변경 요약
- 변경된 모듈:
- 변경 이유:
- 호환 계층 유지 여부:

### 검증
- 파일 내용 확인:
- `git diff` 확인:
- unit/integration/E2E 실행 결과:
- 수동 확인 화면 또는 경로:

### 미완료 항목
- 남은 TODO:
- 다음 단계 선행 조건 충족 여부:

## 9. 최종 완료 기준
- detector/composer/execution policy가 분리된 공통 코어가 존재한다.
- 기존 대표 전략 2종 이상이 새 코어 위에서 동작한다.
- explain, logs, backtest 경로가 새 객체를 기준으로 일관되게 동작한다.
- worker placeholder가 제거된다.
- 문서와 코드가 같은 구조를 설명한다.

## 10. 이번 문서의 즉시 후속 작업
- 각 단계별 첫 PR 범위를 이 문서 기준으로 확정
- `smc_confluence_v1` 이관용 세부 TODO 작성
- fixture 준비 작업 시작
