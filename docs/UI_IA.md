# UI_IA.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

참조:
- 시각 스타일 SSOT: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- AI UI 구현 가드레일: [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md)
- 실시간 모니터링 상세 동작: [MONITORING_SCREEN_SPEC.md](./MONITORING_SCREEN_SPEC.md)
- API 계약: [API_PAYLOADS.md](./API_PAYLOADS.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

## 문서 역할
- 이 문서는 화면별 목적, 메뉴, 섹션 구조를 정의한다.
- 실제 색상, 타이포그래피, spacing, 카드/버튼/테이블의 룩앤필은 `DESIGN_SYSTEM.md`를 따른다.
- 구현 시 밀도와 일관성 검증은 `AI_UI_STYLE_GUIDE.md`를 따른다.

## 공통 화면 제작 원칙
- 공통 앱 셸은 좌측 내비게이션, 상단 헤더, 메인 콘텐츠 캔버스를 기본으로 한다.
- 각 화면은 `Page Header > Summary > Filters/Controls > Main Content > Secondary Info` 리듬을 우선한다.
- 화면당 강한 primary CTA는 영역별 1개만 둔다.
- KPI, 상태, 경고, 로그는 카드/칩/테이블 패턴을 재사용한다.
- 화면이 좁아질수록 보조 정보와 보조 패널이 아래로 내려가도록 구성한다.

## 메인 메뉴
- Dashboard
- Monitoring
- Strategies
- Backtests
- Compare
- Logs
- Settings

## 1. Dashboard
Data source:
- `GET /api/v1/monitoring/summary`
목적:
- 전체 시스템 상태와 핵심 전략 성과 요약

섹션:
- 상단 상태 바
- 전략 요약 카드
- 후보군 요약
- 리스크 경고 패널
- 최근 신호 피드

권장 컴포넌트:
- `StatusChip`
- `MetricCard`
- `DataTable` 또는 `SignalFeedList`

시각 메모:
- 요약 KPI는 카드 행으로 배치하고, 경고 영역만 semantic color를 강하게 사용한다.
- 최근 신호 피드는 dense table/list 스타일을 사용한다.

## 2. Monitoring
목적:
- 단일 전략 세션을 최대 4개까지 병렬 관찰 및 비교

레이아웃:
- 좌측: 세션 선택 및 비교 패널
- 중앙: 차트 영역
- 우측: 실시간 신호/포지션/주문 요약
- 하단: 로그/이벤트 탭

우측 요약 필수 항목:
- 매수/매도 신호
- 매수/매도가
- 손절/익절가
- 실현/미실현 손익
- 손익률
- duplicate block/risk block 여부

권장 컴포넌트:
- `SessionSelector`
- `ChartCard`
- `SegmentedControl`
- `StatusChip`
- `DataTable`

시각 메모:
- 중앙 차트가 화면의 시각적 중심이어야 한다.
- 선택 세션과 현재 심볼에만 accent를 사용하고 나머지는 중립 톤으로 유지한다.
- 상세 상호작용과 상태 표현은 `MONITORING_SCREEN_SPEC.md`를 따른다.

Implementation note (2026-03-14):
- The monitoring screen now uses a three-column layout.
- Left column: stacked tables for `Strategy -> Session -> PnL`.
- Center column: chart workspace.
- Right column: `Session Detail` tabs with `Event Log / Strategy Explain / Signals / Orders / Risk`.
- The old `Position` tab was removed from session detail.
- PnL rows derive from session positions plus `WS /ws/prices` live prices for the session's active symbols.
- The active session-detail tab refreshes on a 2-second interval in the monitoring screen.
- Session list/header refresh is slower than detail polling, and position snapshots refresh separately for live PnL support.
- New rows in the event log, signal, order, and risk tables use the same animated row-enter behavior as the dashboard.

## 3. Strategies - List
테이블 컬럼:
- 전략명
- 최신 버전
- 타입
- 태그
- 활성 여부
- 최근 7일 성과
- 최근 수정일
- 액션(상세/편집/백테스트/실행)

권장 컴포넌트:
- `FilterBar`
- `DataTable`
- `StatusChip`

시각 메모:
- 전략 목록은 dense table 우선이며, 카드 나열형 레이아웃은 기본값으로 사용하지 않는다.

## 4. Strategy Detail
섹션:
- 헤더
- 최신 버전 요약
- JSON 개요
- 성과 카드
- 버전 이력
- 노트/회고
- 관련 백테스트
- 관련 세션

권장 컴포넌트:
- `SummaryCard`
- `JsonPreviewCard`
- `HistoryTable`

시각 메모:
- 상단 요약과 성과 카드를 먼저 배치하고, 이력/노트/연관 리소스는 아래로 분리한다.

## 5. Strategy Edit
탭:
- Basic
- Market & Universe
- Entry
- Reentry
- Position
- Exit
- Risk
- Execution
- Backtest
- JSON Editor
- Validation

원칙:
- Form + JSON 동기화
- validation 결과 즉시 표시
- diff preview 제공
- 전략 생성과 전략 편집은 같은 탭 구조와 동일한 structured editor 패턴을 사용한다.
- `Entry / Reentry / Exit`는 raw JSON만 노출하지 말고 조건 타입, indicator length, lookback, threshold 같은 parameter를 구조화 폼으로 편집할 수 있어야 한다.
- Explain/debug payload에 노출되는 parameter 이름과 값은 편집 폼에서 설정한 항목과 대응되어야 한다.

권장 컴포넌트:
- `SectionTabs`
- `FormSection`
- `ValidationPanel`
- `DiffPreviewPanel`

시각 메모:
- 긴 입력 폼은 섹션과 탭으로 쪼개고, 저장 액션 위치는 일관되게 유지한다.
- 폼과 JSON preview는 서로 다른 card 스타일을 만들지 말고 공통 surface 패턴을 재사용한다.

## 6. Backtests
탭:
- Run New
- History
- Result Detail

시각 메모:
- 실행 입력, 결과 요약, equity chart, trade table의 위계가 분명해야 한다.

## 7. Compare
비교 항목:
- 비교 단위는 세션이며, 각 세션은 `strategy_version_id` 1개에 귀속된다
- 총수익률
- MDD
- 승률
- Profit Factor
- 거래 수
- 평균 보유 시간
- 샤프비율
- 최근 성과
- 종목별 편차

시각 메모:
- 비교 화면은 여러 개의 화려한 카드보다 공통 기준 표와 비교 차트를 우선한다.

## 8. Logs
탭:
- System
- Market Ingest
- Strategy Execution
- Order Simulation
- Risk Control
- Document Change

시각 메모:
- 로그 화면은 필터 바 + dense table + detail drawer 흐름을 기본으로 한다.

## 9. Settings
- Upbit 연결 설정
- Storage 설정
- Universe 정책
- UI 차트 설정
- Risk 기본값
- Live 보호 설정

시각 메모:
- 설정 화면은 섹션 타이틀, helper text, form group, 저장 액션의 리듬을 일관되게 유지한다.
