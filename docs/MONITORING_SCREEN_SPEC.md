# MONITORING_SCREEN_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 실시간 모니터링 화면의 실제 동작 명세다.  
`UI_IA.md`가 정보 구조라면, 이 문서는 `/monitoring` 라우트의 구현 기준이다.

참조:
- 정보 구조: [UI_IA.md](./UI_IA.md)
- 시각 스타일 SSOT: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- AI UI 구현 가드레일: [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md)
- API 계약: [API_PAYLOADS.md](./API_PAYLOADS.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

---

## 2. 화면 목표
- 최대 4개 세션을 동시에 관찰
- 동적 후보군의 현재 감시 종목을 한눈에 파악
- 실시간 신호, 포지션, 손익, 리스크 블록을 즉시 확인
- PAPER/LIVE 상태를 분명히 구분
- 차트와 표가 동일 snapshot 기준으로 보이도록 동기화

## 2.1 시각 구현 기준
- 이 화면의 색상, 타이포그래피, spacing, radius, glow는 `DESIGN_SYSTEM.md`를 따른다.
- 레이아웃 밀도와 강조 규칙은 `AI_UI_STYLE_GUIDE.md`를 따른다.
- 모니터링 화면은 Coin Lab에서 가장 정보 밀도가 높은 화면이므로, 장식보다 차트와 상태 가독성을 우선한다.
- 중앙 차트 패널이 시각적 주인공이며, 좌우 패널은 동일한 base surface 패턴 안에서 정보만 다르게 배치한다.

---

## 3. 라우트
- `/monitoring`
- `/monitoring?sessionId=ses_001`
- `/monitoring?sessionId=ses_001&symbol=KRW-BTC&timeframe=5m`

---

## 4. 데이터 소스

### React Query
- monitoring summary
- session detail
- session positions
- session orders
- recent risk events
- strategy metadata

### WebSocket
- connection state
- active universe updates
- signal stream
- position updates
- chart points
- risk alerts
- session health updates

### Zustand
- selected session
- selected compare session ids
- selected symbol
- selected timeframe
- chart overlay toggles
- panel layout mode
- table sort/filter state

---

## 5. 상단 글로벌 바

### 5.1 좌측
- 현재 mode badge: `PAPER` 또는 `LIVE`
- session status chip
- selected session id
- selected strategy version id
- started_at
- active comparison session count
- active symbol count

### Summary contract
- `GET /api/v1/monitoring/summary` feeds the dashboard-level `status_bar`, `strategy_cards`, `universe_summary`, `risk_overview`, and `recent_signals` sections.

### 5.2 중앙
- connection state chip
- snapshot consistency chip
- late event count(5m)
- reconnect count(1h)

### 5.3 우측
- stop
- emergency kill
- manual refresh
- live safety banner

### 상태 색상
- PAPER: `info`
- LIVE: `danger`
- FAILED: `danger`
- RUNNING: `success`
- STOPPED: neutral surface + muted text
- RECONNECTING/DEGRADED: `warning`

---

## 6. 레이아웃 구조

### 기본 3열
1. 좌측: 전략/세션/후보군 패널
2. 중앙: 차트 패널
3. 우측: 신호/포지션/주문/리스크 패널

### 하단 고정 탭
- Event Log
- Strategy Explain
- Order Timeline
- Risk Events

### 반응형 규칙
- 1600px 이상: 3열 고정
- 1200~1599px: 우측 패널 축소
- 1199px 이하: 우측 패널 drawer 전환

### 패널 스타일 규칙
- 좌측/우측/하단 패널은 `Base Card` 계열 surface를 사용한다.
- 현재 선택 세션, 현재 선택 심볼, 주요 CTA만 accent 처리한다.
- LIVE 배너와 kill switch는 semantic danger를 사용하고 브랜드 그린과 혼용하지 않는다.
- 차트 위 토글과 하단 탭은 compact segmented control 패턴을 사용한다.

---

## 7. 좌측 패널 상세

## 7.1 Session Selector
컬럼:
- session id
- mode
- status
- strategy version id
- started_at
- active symbol count

동작:
- 세션 선택 시 전체 화면 context 전환
- 선택 변경 시 미확인 LIVE 경고 있으면 confirm modal 표시

시각 규칙:
- 선택된 세션 row 또는 카드만 accent border/glow 허용
- 미선택 세션은 neutral surface 유지

## 7.2 Session Compare List
최대 4개 세션 표시.
컬럼:
- 체크박스
- 전략명
- 버전
- 최근 신호 시간
- realized pnl
- unrealized pnl
- win rate
- risk blocks(최근 1h)

정렬 기본값:
- unrealized pnl desc

## 7.3 Active Universe List
컬럼:
- symbol
- 24h turnover
- recent surge score
- selected badge
- active comparison session count

필터:
- watchlist only
- with open position
- with recent signal
- risk-blocked only

시각 규칙:
- 심볼 선택 상태는 chip 또는 row highlight로 표시한다.
- risk-blocked 심볼은 warning semantic을 사용하되 과한 배경색으로 전체 리스트를 오염시키지 않는다.

---

## 8. 중앙 차트 패널

## 8.1 헤더
- selected symbol
- selected timeframe
- compared session multi-select dropdown
- timeframe toggle: `tick | 1m | 5m | 15m`
- overlay toggle:
  - MA
  - RSI
  - volume
  - signal markers
  - stop/take-profit lines
  - active orders

## 8.2 차트 구성
- Main candle chart
- Volume sub-panel
- Optional RSI sub-panel

### 필수 overlay
- buy/sell marker
- stop loss line
- take profit line
- trailing stop line
- pending order price line

### 규칙
- 4개 세션 동시 비교 시 marker 색상 대신 shape/label도 구분
- 차트 스케일 이동은 현재 symbol 기준 유지
- websocket late event로 재계산 발생 시 chart sync badge 표시
- grid, tooltip, crosshair, chart toolbar는 `DESIGN_SYSTEM.md`의 chart/container 규칙을 따른다

## 8.3 차트 interaction
- crosshair hover 시 우측 패널 값 동기화
- marker 클릭 시 해당 signal을 selected signal로 설정하고 하단 `Strategy Explain` 탭으로 이동
- order line 클릭 시 하단 `Order Timeline` 탭 이동

---

## 9. 우측 패널

## 9.1 Recent Signals 카드
컬럼:
- time
- strategy
- symbol
- action
- signal price
- confidence
- blocked 여부
- reason codes 요약

동작:
- 행 클릭 시 차트 이동
- blocked signal은 amber row highlight

시각 규칙:
- action은 semantic chip 또는 icon과 함께 표시한다.
- blocked signal은 `warning` semantic으로 표시하되, 선택 row 강조와 혼동되지 않게 한다.

## 9.2 Open Positions 카드
컬럼:
- strategy
- symbol
- qty
- avg entry
- current price
- stop loss
- take profit
- realized pnl
- unrealized pnl
- unrealized pnl %
- status

정렬 기본값:
- unrealized pnl asc

### 강조 규칙
- 손실 포지션은 색상 강조
- stop loss 근접 임계치 도달 시 warning icon
- trailing stop 활성 중이면 special chip
- 수익/손실 숫자는 tabular numeric을 사용한다

## 9.3 Orders 카드
컬럼:
- submitted time
- strategy
- symbol
- role
- type
- state
- requested price
- executed price
- qty
- retry count

### 상태 아이콘
- OPEN: amber
- PARTIALLY_FILLED: blue
- FILLED: green
- REJECTED/FAILED: red

시각 규칙:
- 주문 상태는 text만 두지 말고 chip/icon 조합으로 보여준다.

## 9.4 Risk Panel
항목:
- daily loss limit usage
- max drawdown usage
- duplicate block count
- recent risk events

긴급 상황:
- LIVE에서 kill switch 발동 시 패널 맨 위 pinned alert

시각 규칙:
- risk usage progress는 neutral track + semantic fill 조합으로 표시한다.
- pinned alert는 우측 패널 최상단에 고정하고 scroll로 사라지지 않게 한다.

---

## 10. 하단 탭

## 10.1 Event Log
필터:
- level
- strategy_version_id
- symbol
- event_type

컬럼:
- time
- level
- source
- message

## 10.2 Strategy Explain
선택된 signal 기준:
- snapshot key
- matched conditions
- failed conditions
- facts/value table
- parameters table
- blocked reason
- raw explain json

## 10.3 Order Timeline
선택된 position/order 기준:
- created
- submitted
- partial fill
- cancel
- fallback
- final fill

## 10.4 Risk Events
컬럼:
- time
- severity
- code
- symbol
- strategy_version_id
- payload preview

---

## 11. 상태별 UX

## 11.1 Loading
- skeleton layout 표시
- 이전 데이터 retain 가능
- selected symbol chart는 stale badge 표시
- skeleton은 최종 카드 구조와 동일한 레이아웃을 유지한다

## 11.2 Empty
경우:
- 세션 없음
- universe 비어 있음
- signal 없음
- position 없음

각 empty state는 단순 빈 화면이 아니라 다음 행동 CTA 포함:
- 세션 시작
- watchlist 확인
- 비교 세션 선택
- 데이터 연결 상태 점검

시각 규칙:
- empty state도 base card 안에서 설명 + 보조 CTA 조합으로 처리한다.

## 11.3 Error
분류:
- API load error
- websocket disconnected
- chart sync error
- session health degraded

동작:
- retry button
- 마지막 정상 시각 표시
- LIVE면 persistent banner 유지

시각 규칙:
- full-page error보다 scoped error card를 우선 사용하되, LIVE 장애는 persistent banner를 유지한다.

---

## 12. LIVE 안전 UX
- 상단 red persistent banner
- stop보다 더 눈에 띄는 `EMERGENCY KILL` 버튼
- mode 혼동 방지 위해 PAPER/LIVE 색상 체계 완전 분리
- LIVE에서는 mock badge/estimated fill 용어 금지
- LIVE 시작 후 5초간 session status를 `PENDING`으로 두고 안전 점검 메시지 표시 가능
- LIVE 관련 danger 표현은 여기서만 강하게 사용하고, 일반 활성 상태와 섞지 않는다

---

## 13. 세션 4개 병렬 비교 규칙
- 세션별 색상/shape 조합 고정
- 비교 표에서는 최소 지표 8개 고정:
  - total return
  - MDD
  - win rate
  - profit factor
  - trade count
  - avg hold
  - realized pnl today
  - unrealized pnl now
- 차트 마커 과밀 시 현재 선택 세션 우선 렌더
- 나머지 세션은 축약 표기 또는 toggle off 허용

---

## 14. 성능 규칙
- chart stream은 batch update
- recent signals list는 max 200 visible rows
- event log는 virtualization 권장
- 1초 내 다건 신호는 summary aggregation 카드도 제공 가능
- symbol 전환 시 이전 subscription cleanup 필수

---

## 15. API 매핑
- `/api/v1/sessions/{sessionId}`
- `/api/v1/sessions/{sessionId}/positions`
- `/api/v1/sessions/{sessionId}/orders`
- `/api/v1/sessions/{sessionId}/signals`
- `/api/v1/sessions/{sessionId}/risk-events`
- `WS /ws/monitoring`
- `WS /ws/charts/{symbol}`
- `WS /ws/prices?symbols=KRW-BTC,KRW-ETH`

### Implementation Addendum (2026-03-14)
- Left column: `Strategy -> Session -> PnL` stacked tables
- Center column: chart workspace
- Right column: `Session Detail` tabs
- Session detail tabs: `Event Log / Strategy Explain / Signals / Orders / Risk`
- The old `Position` detail tab is removed.
- Monitoring page PnL rows now derive from session position snapshots plus `WS /ws/prices` live symbol prices.
- The active session-detail tab polls every 2 seconds for live updates.
- Session header/session-list refresh uses a slower cadence than detail polling, and position snapshots refresh separately for live PnL support.
- Monitoring summary still accepts websocket-driven cache updates through `WS /ws/monitoring`.
- Newly inserted rows in `Event Log`, `Signals`, `Orders`, and `Risk` reuse the same animated table-row enter behavior as the dashboard.
- `Signals` rows act as the selector for the `Strategy Explain` detail view in the monitoring screen.
- Chart signal markers and `Signals` rows both update the same selected-signal state used by `Strategy Explain`.

---

## 16. Codex 구현 체크리스트
- 차트, signals, positions가 같은 selected symbol/timeframe context를 공유하는가
- LIVE banner가 충분히 눈에 띄는가
- 실시간 disconnect 상태가 숨겨지지 않는가
- blocked signal과 실제 emitted signal이 구분되는가
- stop/take-profit/current pnl 정보가 우측 패널과 차트에서 동시에 보이는가
