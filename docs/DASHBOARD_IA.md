# DASHBOARD_IA.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 현재 `/` 대시보드 화면의 정보 구조와 섹션 구성 기준을 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-21
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 문서 역할
이 문서는 현재 구현된 Dashboard 화면의 IA 전용 문서다.

- 시각 스타일 SSOT: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- AI UI 가드레일: [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md)
- 라우트 레벨 IA 상위 문서: [UI_IA.md](./UI_IA.md)
- 데이터 공급: `GET /api/v1/monitoring/summary`

이 문서는 특히 아래를 명확히 한다.

- 현재 대시보드가 무엇을 중심 객체로 삼는지
- 섹션이 어떤 순서로 배치되는지
- 각 섹션이 어떤 데이터를 보여주는지
- 어떤 섹션이 다른 화면으로 이어지는지

## 2. 화면 목적
- 전략 실험실의 현재 상태를 한 화면에서 요약한다.
- AI 모델이 아니라 `전략`을 중심 객체로 본다.
- 실행 중인 전략, 최근 체결, 성과 흐름, 전략 비교, 실험 대상 마켓을 빠르게 훑을 수 있어야 한다.
- 사용자가 대시보드에서 `모니터링`, `전략 상세`, `마켓 관찰`로 자연스럽게 이동할 수 있어야 한다.

## 3. 핵심 개념

### 3.1 중심 객체
- `전략(strategy)`

### 3.2 보조 객체
- `세션(session)`
- `심볼(symbol)`
- `실시간 활동(signal / order / risk event)`
- `전략 성과(performance)`

### 3.3 정보 해석 규칙
- 첨부 레퍼런스의 `AI 모델` 개념은 Coin Lab에서 `전략`으로 치환한다.
- 첨부 레퍼런스의 `모델 상세 카드`는 `전략 상세 카드`로 해석한다.
- 첨부 레퍼런스의 `leaderboard`는 `전략 성과 비교표`로 해석한다.

## 4. 라우트
- `/`

## 5. 데이터 소스

### 5.1 기본 API
- `GET /api/v1/monitoring/summary`

### 5.2 현재 화면에서 사용하는 대시보드 summary 하위 블록
- `dashboard.performance_history`
- `dashboard.live_activity`
- `dashboard.recent_trades`
- `dashboard.leaderboard`
- `dashboard.strategy_details`
- `dashboard.market_details`

특기 사항:
- `dashboard.strategy_details.entry_readiness` 는 심볼별 최근 체결 비율이 아니라, 현재 전략 로직의 진입/청산 준비도를 `0~100%`로 정규화한 값이다.

참고:
- `status_bar`
- `universe_summary`
- `risk_overview`
- `dashboard.hero`
- `dashboard.strategy_strip`
- `dashboard.market_strip`
- 위 블록들은 API 응답에 포함될 수 있지만, 현재 `/` 대시보드 본문에는 렌더링하지 않는다.

## 6. 전체 레이아웃 구조

대시보드는 아래 순서를 따른다.

1. Performance History + Live Activity
2. Recent Trades
3. Leaderboard
4. Strategy Details Grid
5. Market Details

원칙:
- 상단일수록 비교와 흐름
- 중단은 비교와 흐름
- 하단은 상세 탐색

## 7. 섹션별 IA

## 7.1 Performance History
목적:
- 전략별 최근 성과 흐름을 비교한다.

구성:
- 섹션 제목
- Best strategy 요약 칩
- SVG 기반 다중 라인 차트
- 전략 legend 칩 목록

표현 단위:
- x축: 최근 체결 기준 시점/상대 구간
- y축: 전략 수익률
- line color: 전략별 구분
- 하단 legend 칩: `brand.primary` 계열 블루 accent 사용
- semantic `success`/`danger`는 상태 의미가 있을 때만 사용

중심 메시지:
- 지금 어떤 전략이 상대적으로 우세한지
- 수익률 방향이 상승/하락 중인지

## 7.2 Live Activity
목적:
- 최근 발생한 실시간 이벤트를 하나의 피드에서 본다.

이벤트 유형:
- signal
- order
- risk

각 행 구성:
- 이벤트 제목
- 전략명
- 심볼
- 상세 설명
- 상대 시간

의미:
- 신호, 체결, 리스크를 분리된 표가 아니라 하나의 활동 피드로 통합해 문맥을 빠르게 파악하게 한다.

## 7.3 Recent Trades
목적:
- 최근 체결 로그를 dense table로 확인한다.

컬럼:
- 전략
- 체결 역할
- 심볼
- 수량
- 가격
- 시간

행 의미:
- 전략이 실제로 어떤 체결을 만들었는지
- ENTRY/EXIT/TP/SL 흐름의 최근 결과

## 7.4 Leaderboard
목적:
- 전략 성과를 표준 지표로 비교한다.

컬럼:
- 순위
- 전략명
- 타입
- 활성 세션 수
- 계정 가치
- 실현/평가 손익
- 수익률
- 승률
- 거래 수
- 리스크 알림 수

중심 메시지:
- 어떤 전략이 현재 실험실에서 가장 성과가 좋은가
- 성과가 좋아도 리스크 이벤트가 많은 전략은 무엇인가

## 7.5 Strategy Details Grid
목적:
- 전략을 카드 단위로 더 자세히 본다.

카드 구성:
- 전략 모노그램
- 전략명
- 전략 타입
- 계정 가치
- 총 수익률
- 실현 손익
- 승률
- 코인별 전략 진입률(%)
- 활성 포지션 preview
- `열기` 액션

진입률 규칙:
- 각 전략의 실제 entry/exit 계산식을 기준으로 심볼별 `%`를 만든다.
- 동일 심볼이라도 전략이 다르면 다른 값이 나올 수 있다.
- 시장 체결의 `buy/sell` 비중을 공통으로 재사용하지 않는다.

행동:
- `열기` 클릭 시 전략 상세 페이지 이동

## 7.6 Market Details
목적:
- 실험 대상 심볼을 아코디언 형태로 탐색한다.

요약 헤더:
- 심볼명
- 24h 거래대금
- 선택/포지션/최근신호/리스크 상태 칩

펼침 영역:
- 활성 비교 세션 수
- surge score
- 리스크 상태

의미:
- 대시보드 하단에서 “현재 어떤 마켓이 실험실 맥락에 들어와 있는지”를 확인한다.

## 8. 반응형 규칙

### 8.1 넓은 화면
- Performance History와 Live Activity는 8:4 분할
- Strategy Details는 3열 카드

### 8.2 중간 화면
- Performance / Activity는 세로 스택 가능
- Strategy Details는 2열

### 8.3 작은 화면
- 모든 섹션은 단일 컬럼
- 차트 legend 칩은 줄바꿈 허용
- 테이블은 dense 유지하되 가독성 우선

## 9. 사용자 흐름

### 9.1 전체 상태 확인
1. Performance History에서 우세 전략과 성과 흐름 확인
2. Live Activity에서 최근 신호, 체결, 리스크 맥락 확인
3. 필요 시 Leaderboard와 Strategy Details로 비교 범위 확장

### 9.2 전략 탐색
1. Leaderboard에서 성과가 좋은 전략 확인
2. Strategy Details 카드에서 맥락 확인
3. 전략 상세 페이지로 이동

### 9.3 실시간 실행 확인
1. Live Activity에서 최근 이벤트 확인
2. Recent Trades에서 체결 내역 확인
3. 필요 시 모니터링 화면으로 이동

### 9.4 마켓 탐색
1. Strategy Details 카드에서 전략별 포지션 맥락 확인
2. Market Details 아코디언에서 심볼 상태 상세 확인

## 10. 정보 계층 우선순위
- Level 1: Performance History, Live Activity
- Level 2: Leaderboard, Strategy Details
- Level 3: Recent Trades, Strategy Details
- Level 4: Market Details, 보조 메타 정보

## 11. 구현 기준 파일
- 페이지 구현: [DashboardPage.tsx](/Users/chanchan2/Desktop/coin-lab-v2/frontend/src/pages/DashboardPage.tsx)
- 공통 surface: [LabSurfaceCard.tsx](/Users/chanchan2/Desktop/coin-lab-v2/frontend/src/shared/ui/LabSurfaceCard.tsx)
- 데이터 타입: [api.ts](/Users/chanchan2/Desktop/coin-lab-v2/frontend/src/features/monitoring/api.ts)
- 백엔드 집계: [monitoring_service.py](/Users/chanchan2/Desktop/coin-lab-v2/backend/app/application/services/monitoring_service.py)

## 12. 설계 메모
- 이 화면은 “운영자용 콘솔”이면서 동시에 “전략 실험 전광판”의 성격을 가진다.
- 따라서 참조 이미지의 정보 구조를 차용하되, 전역 LNB는 유지하고 본문은 `흐름 + 비교 + 상세` 구조로 압축한다.
- 화면의 중심 객체는 AI 모델이 아니라 전략이며, IA도 그 기준으로 유지한다.
