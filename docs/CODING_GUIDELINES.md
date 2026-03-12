# CODING_GUIDELINES.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 코인 전략 실험실 프로젝트의 공통 코딩 규칙 문서다.  
목표는 다음 5가지를 동시에 만족하는 것이다.

1. 실시간 반응성
2. 모듈화
3. 재사용성
4. 유지보수성
5. 실전 자동매매 확장성

이 문서는 `AGENT.md`, `ARCHITECTURE.md`, `EVENT_FLOW.md`, `STATE_MACHINE.md`, `DB_SCHEMA.md`, `API_SPEC.md`보다 하위 구현 규칙을 정의하는 **구현 SSOT**다.

---

## 2. 공통 원칙

### 2.1 단일 책임
- 하나의 함수는 하나의 책임만 가진다.
- 하나의 컴포넌트는 하나의 UI 책임만 가진다.
- 하나의 서비스는 하나의 도메인 작업만 담당한다.
- 전략 평가, 주문 시뮬레이션, UI 렌더링을 같은 파일에 섞지 않는다.

### 2.2 명시적 타입
- TypeScript는 `any` 금지.
- Python은 공개 함수/메서드에 타입 힌트를 강제한다.
- API request/response는 schema 기반으로만 정의한다.
- DB JSON 컬럼도 내부 shape를 문서화한다.

### 2.3 파생 상태 최소화
- 계산 가능한 값은 저장하지 않는다.
- 프론트에서 총합/손익률/정렬용 파생 값은 selector 또는 memoized 계산으로 처리한다.
- 백엔드에서 `snapshot`으로 계산 가능한 값은 중복 저장하지 않는다.

### 2.4 로그 없는 자동화 금지
다음 동작은 반드시 로그를 남겨야 한다.
- 전략 진입/청산 결정
- 리스크 차단
- 주문 재시도
- 세션 중지/kill
- 문서/스키마 변경
- websocket 재연결

### 2.5 문서 없는 확장 금지
아래 항목을 문서 없이 임의 추가하지 않는다.
- enum 값
- strategy operator
- API field
- DB column
- session state
- order state

---

## 3. React / TypeScript 규칙

### 3.1 컴포넌트 구조
분류 기준:
- `pages/`: route 단위 조합
- `features/`: 도메인 단위 기능
- `components/`: 재사용 가능한 표현 컴포넌트
- `hooks/`: UI와 외부 시스템 동기화 또는 복합 상태 로직
- `stores/`: Zustand store
- `lib/`: 포맷터, selector, 계산 유틸, chart adapter

### 3.2 컴포넌트 책임 규칙
허용:
- props 받아 렌더링
- 단순 로컬 UI 상태
- 이벤트 전달

금지:
- 전략 계산 로직
- websocket raw message 파싱
- API payload shape 결정
- 서버 캐시를 직접 mutation 하는 비즈니스 규칙

### 3.3 상태 관리 역할 분리
#### React Query
사용 범위:
- 전략 목록/상세 조회
- 버전 목록
- 백테스트 결과 조회
- 로그 조회
- 서버 메타데이터 조회

금지:
- 초당 수십 건 이상 밀려오는 실시간 tick stream을 React Query cache에 누적 저장
- chart live feed 전체를 query cache에 보관

#### Zustand
사용 범위:
- UI filter
- 탭/패널 선택 상태
- 선택 전략/세션
- 실시간 모니터링 화면의 휘발성 view model
- websocket 연결 상태 badge
- 차트 표시 옵션

금지:
- server source of truth 전체 복제
- 전략 목록 전체 캐시 저장소로 사용

### 3.4 effect 규칙
`useEffect` 허용:
- websocket 연결/해제
- timer 등록/해제
- DOM 외부 라이브러리 동기화
- route 전환 시 외부 시스템 clean-up

`useEffect` 금지:
- props를 다른 state로 복사하는 용도
- 렌더링 중 계산 가능한 파생 값을 state에 저장하는 용도
- effect 체인으로 비즈니스 로직 연결

### 3.5 memoization 규칙
- 무거운 계산: `useMemo`
- 자식 re-render 비용이 높은 콜백: `useCallback`
- 대형 표/차트 셀 렌더러: `memo`
- 남용 금지. 측정 없이 전역적으로 쓰지 않는다.

### 3.6 렌더링 성능 규칙
- 리스트는 stable `key` 사용. index key 금지.
- 500행 이상 표는 virtualization 고려.
- chart update는 batch 처리. tick마다 전체 component tree re-render 금지.
- 1초 내 다건 갱신은 `requestAnimationFrame` 또는 throttle adapter 고려.

### 3.7 form + JSON editor 동기화 규칙
- form state가 1차 편집 원본
- JSON editor는 canonical serialized view
- 양방향 sync는 schema 기반 transformer를 통해 수행
- parse 실패 시 JSON editor만 invalid 상태로 표시하고 form state는 즉시 파괴하지 않음
- unknown field는 기본적으로 저장 금지. 필요 시 `extensions` 아래만 허용

### 3.8 UI 에러 처리
- 사용자 조치 가능한 에러는 화면 메시지 표시
- 재시도 가능한 에러는 CTA 제공
- LIVE 차단 관련 에러는 snackbar로 끝내지 않고 persistent warning panel로 보여줌

---

## 4. MUI 규칙
- theme token 우선, inline style 남용 금지
- spacing scale 고정: 4, 8, 12, 16, 24, 32
- dashboard density는 compact variant 기준
- 공통 래퍼 컴포넌트 사용:
  - `AppCard`
  - `MetricCard`
  - `SectionHeader`
  - `StatusChip`
  - `DangerBanner`
- DataGrid column definition은 파일별 중복 작성 금지. feature 단위 column builder 사용

---

## 5. lightweight-charts 규칙
- 원본 데이터와 차트 series 어댑터 분리
- candle, volume, signal marker, stop/take-profit line을 레이어 분리
- chart 라이프사이클과 data 라이프사이클 분리
- 차트 컴포넌트는 raw tick을 직접 받지 않고 normalized point stream을 받는다
- series 재생성보다 `update()` 우선
- 종목/시간프레임 전환 시 이전 subscription cleanup 필수

---

## 6. Python / FastAPI 규칙

### 6.1 계층 구조
- `domain/`: 엔티티, 값 객체, enum, 전략 인터페이스
- `application/`: use case, orchestration, command/query service
- `infrastructure/`: upbit adapter, db repository, file logger, cache, queue
- `api/`: FastAPI router, request/response schema
- `workers/`: long-running worker 진입점

### 6.2 함수/클래스 규칙
- 공개 함수는 타입 힌트 필수
- 40줄 이상 함수는 분리 검토
- 하나의 클래스가 외부 시스템 2개 이상 직접 다루지 않는다
- side effect가 있는 함수 이름은 동사형으로 명시 (`start_session`, `persist_signal`)

### 6.3 Pydantic 규칙
- 외부 입출력은 반드시 pydantic schema 사용
- dict를 raw로 주고받는 API 금지
- schema에 validation rule 명시
- enum/string union은 문서와 동일해야 함

### 6.4 예외 처리 규칙
- broad `except Exception` 금지. 경계 계층에서만 허용
- domain error / infra error / retryable error 구분
- retryable 예외는 error code와 retry hint를 함께 생성
- API는 stacktrace를 노출하지 않는다

### 6.5 async 규칙
- websocket, io-bound 저장, 외부 API 호출은 async 우선
- CPU-bound backtest는 worker process로 격리
- async 함수는 timeout/cancel 전략을 가진다
- cancellation 시 partial side effect 정리 규칙 필요

### 6.6 자원 관리
- 파일/DB/소켓 핸들은 context manager 또는 lifespan hook으로 관리
- worker 종료 시 outstanding queue flush 정책 명시
- reconnect loop는 jitter를 가진 backoff 사용

---

## 7. 실시간 처리 규칙

### 7.1 raw payload 직접 사용 금지
흐름은 항상 아래와 같다.
1. raw websocket message
2. normalized event
3. snapshot update
4. strategy evaluation
5. order intent
6. execution adapter
7. persisted record

### 7.2 시간 필드
모든 핵심 이벤트는 아래를 분리한다.
- `event_time`: 거래소 기준 이벤트 발생 시각
- `received_time`: 우리 프로세스 수신 시각
- `processed_time`: 내부 처리 완료 시각

### 7.3 dedupe / idempotency
- raw event는 `source + channel + sequence_or_trade_id` 기반 dedupe
- signal은 `session_id + strategy_version_id + symbol + timeframe + signal_action + snapshot_key` 기반 dedupe
- order는 `idempotency_key` 필수
- 같은 `idempotency_key`는 상태 재기록만 허용, 신규 생성 금지

### 7.4 reconnect 규칙
- connection state: `CONNECTING | OPEN | DEGRADED | RECONNECTING | CLOSED`
- 1회 실패로 session stop 금지
- reconnect 후 gap recovery 없으면 `snapshot_consistency = degraded`
- degraded 상태에서는 LIVE 신규 진입 차단 가능

### 7.5 out-of-order 규칙
- sequence 존재 시 sequence 우선
- sequence 없음 + event_time 역전 시 허용 윈도우 내 reorder buffer 사용
- reorder window 초과 이벤트는 `late_event`로 기록하고 snapshot 재계산 정책에 따라 처리

---

## 8. 테스트 규칙
- 새 operator 추가 시 validator/evaluator/form mapper 테스트 동시 추가
- session state 변경 시 state-machine test 추가
- execution simulation 수정 시 golden scenario 테스트 업데이트
- websocket adapter는 reconnect, duplicate, gap recovery 테스트 포함
- chart 관련 로직은 UI snapshot보다 adapter 단위 테스트 우선

---

## 9. 금지 패턴
- UI component에서 전략 평가
- effect에서 API 응답을 다른 state로 복사하여 관리
- raw websocket payload를 DB에 바로 저장 후 그 레코드를 그대로 UI/엔진이 읽는 구조
- session mode를 if-else로 여기저기 흩뿌리는 구조
- backtest와 live order state enum을 서로 다르게 운영
- 문서에 없는 operator/enum/field 임의 추가
