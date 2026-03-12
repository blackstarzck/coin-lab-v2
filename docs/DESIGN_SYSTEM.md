# Coin Lab 디자인 시스템

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: Coin Lab 화면 구현에 사용하는 시각 SSOT와 공통 디자인 토큰을 정의한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 문서 역할
이 문서는 Coin Lab UI의 시각 표현을 결정하는 기준 문서다.

- 시각 스타일 SSOT: `DESIGN_SYSTEM.md`
- 화면 정보 구조 SSOT: [UI_IA.md](./UI_IA.md)
- 화면별 동작/데이터 SSOT: [MONITORING_SCREEN_SPEC.md](./MONITORING_SCREEN_SPEC.md) 및 각 기능 명세
- AI 구현 가드레일: [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md)

충돌 해석 원칙:

- 정보 구조와 사용자 흐름은 `UI_IA.md`를 따른다.
- API, 상태, 동작은 각 기능 명세를 따른다.
- 색상, 타이포그래피, 간격, 표면, 컴포넌트 룩앤필은 이 문서를 따른다.

## 관련 UI/디자인 문서
- [UI_IA.md](./UI_IA.md): 화면별 목적, 메뉴, 섹션 구조
- [MONITORING_SCREEN_SPEC.md](./MONITORING_SCREEN_SPEC.md): `/monitoring` 라우트 상세 동작과 데이터 기준
- [AI_UI_STYLE_GUIDE.md](./AI_UI_STYLE_GUIDE.md): AI가 화면을 구현할 때 지켜야 할 밀도, 계층, 일관성 규칙
- [DOC_INDEX.md](./DOC_INDEX.md): 전체 문서 그래프와 우선순위

## 화면 제작 적용 순서
1. `UI_IA.md`에서 해당 화면의 목적, 섹션 구조, 필수 정보 블록을 확인한다.
2. `MONITORING_SCREEN_SPEC.md` 같은 화면별 명세에서 동작, 상태, 데이터 계약을 확인한다.
3. 시각 표현은 이 문서의 토큰, 컴포넌트, 레이아웃 규칙으로 구현한다.
4. 마지막으로 `AI_UI_STYLE_GUIDE.md`로 과장된 장식, 밀도 붕괴, 일관성 이탈을 점검한다.

## 1. 디자인 컨셉

이 UI의 핵심 인상은 아래 5가지입니다.

* **Ultra Dark Base**: 거의 검정에 가까운 딥 네이비/차콜 배경
* **Neon Green Accent**: 핵심 액션과 활성 상태에 형광 그린 포인트
* **Soft Glass + Inner Glow**: 카드와 패널에 미세한 글로우와 반투명한 깊이감
* **Dense Financial Layout**: 정보량은 많지만, 카드 분리와 계층으로 정돈
* **Premium Crypto Dashboard Feel**: 게임스럽지 않고, 고급스럽고 긴장감 있는 금융 UI

---

# 2. Foundation

## 2-1. Color System

이미지 기준으로 보면 전체 구조는 다음처럼 나뉩니다.

* 배경: 아주 어두운 블랙/네이비
* 표면: 카드/패널용 다크 그레이-퍼플 톤
* 강조: 네온 그린
* 보조: 미세한 블루/민트/옐로우 포인트
* 상태: 상승/하락 명확 구분

## 2-2. Core Palette

### Neutral / Background

```txt
bg.canvas         #0E0E10
bg.app            #121119
bg.surface-1      #17161F
bg.surface-2      #1D1B26
bg.surface-3      #24222D
bg.elevated       #2A2733
bg.input          #1A1822
bg.sidebar        #15141C
bg-overlay        rgba(8, 8, 12, 0.72)
```

### Accent / Brand

```txt
brand.primary     #22E76B
brand.primary-2   #18C95B
brand.primary-soft rgba(34, 231, 107, 0.14)
brand.primary-glow rgba(34, 231, 107, 0.28)
brand.secondary   #7CFFB2
brand.logo        #1ED760
```

### Text

```txt
text.primary      #F5F7FA
text.secondary    #B7BDC8
text.tertiary     #7E8594
text.disabled     #5A606C
text.inverse      #0F1115
```

### Border / Divider

```txt
border.default    rgba(255,255,255,0.08)
border.soft       rgba(255,255,255,0.05)
border.strong     rgba(255,255,255,0.12)
border-accent      rgba(34,231,107,0.45)
divider           rgba(255,255,255,0.06)
```

### Status

```txt
success           #22E76B
success-soft      rgba(34,231,107,0.12)

danger            #FF5A5F
danger-soft       rgba(255,90,95,0.12)

warning           #F5B942
warning-soft      rgba(245,185,66,0.12)

info              #4DA3FF
info-soft         rgba(77,163,255,0.12)
```

### Chart / Market Semantic

```txt
chart.up          #22E76B
chart.down        #FF5A5F
chart.volume-up   rgba(34,231,107,0.35)
chart.volume-down rgba(255,90,95,0.35)
chart.line        #24E86E
chart.grid        rgba(255,255,255,0.06)
chart.crosshair   rgba(34,231,107,0.35)
```

---

## 2-3. Gradient Tokens

이 화면은 단색보다 **미세한 컬러 틴트 그라데이션**이 중요합니다.

```txt
gradient.app-bg
linear-gradient(180deg, #1B2130 0%, #1A1A22 35%, #1B5C4A 100%)

gradient.card
linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.01) 100%)

gradient.accent-border
linear-gradient(90deg, rgba(34,231,107,0.45), rgba(34,231,107,0.05))

gradient.green-glow
radial-gradient(circle, rgba(34,231,107,0.22) 0%, rgba(34,231,107,0) 70%)
```

---

# 3. Typography

이미지상 느낌은 **Inter / Satoshi / SF Pro / General Sans 계열**이 잘 맞습니다.
실무적으로는 아래처럼 가면 좋습니다.

## Font Family

```txt
font.sans = "Inter", "Pretendard", "SF Pro Display", sans-serif
font.mono = "JetBrains Mono", "SFMono-Regular", monospace
```

## Type Scale

```txt
display.lg   32 / 40 / 700
display.md   28 / 36 / 700
title.lg     24 / 32 / 600
title.md     20 / 28 / 600
title.sm     18 / 24 / 600
body.lg      16 / 24 / 500
body.md      14 / 20 / 500
body.sm      13 / 18 / 500
caption.lg   12 / 16 / 500
caption.sm   11 / 14 / 500
micro        10 / 12 / 600
```

## Typography Rules

* 금액, 수량, PnL, 가격은 **숫자 가독성이 높은 세미볼드**
* 라벨, 메타 정보, 보조 설명은 `text.secondary` 또는 `text.tertiary`
* 실시간 가격 / 수익 / CTA는 accent 또는 semantic color 사용
* 큰 숫자는 monospaced tabular numbers 적용 권장

예시:

```css
font-variant-numeric: tabular-nums;
```

---

# 4. Spacing System

정보가 많은 화면이므로 촘촘하지만 규칙적이어야 합니다.

```txt
space-2   2px
space-4   4px
space-6   6px
space-8   8px
space-10  10px
space-12  12px
space-16  16px
space-20  20px
space-24  24px
space-32  32px
space-40  40px
```

## Layout Rhythm

* 카드 내부 패딩: `16 ~ 20px`
* 섹션 간 간격: `16 ~ 24px`
* 대시보드 그리드 간격: `16px`
* 좌측 사이드바 아이템 간격: `10 ~ 12px`

---

# 5. Radius & Shape

이 UI는 각이 완전히 날카롭지 않고, 그렇다고 너무 둥글지도 않습니다.
전체적으로 **고급스러운 중간 라운드**가 핵심입니다.

```txt
radius.xs   8px
radius.sm   10px
radius.md   12px
radius.lg   16px
radius.xl   20px
radius.pill 999px
```

## Usage

* 버튼: 10~12px
* 입력창: 10~12px
* 카드: 16~20px
* 메인 앱 프레임: 24px 이상
* 작은 탭/필터: pill 또는 10px

---

# 6. Elevation / Shadow / Glow

이 UI는 일반적인 그림자보다 **은은한 외곽 glow + 내부 하이라이트**가 중요합니다.

## Shadow Tokens

```txt
shadow.sm
0 2px 8px rgba(0,0,0,0.24)

shadow.md
0 10px 30px rgba(0,0,0,0.32)

shadow.lg
0 18px 40px rgba(0,0,0,0.4)

shadow.inner
inset 0 1px 0 rgba(255,255,255,0.04)
```

## Glow Tokens

```txt
glow.green.sm
0 0 0 1px rgba(34,231,107,0.28), 0 0 18px rgba(34,231,107,0.18)

glow.green.md
0 0 0 1px rgba(34,231,107,0.38), 0 0 28px rgba(34,231,107,0.22)

glow.panel
0 0 0 1px rgba(255,255,255,0.05), inset 0 1px 0 rgba(255,255,255,0.03)
```

---

# 7. Grid & Layout

## App Shell Structure

권장 레이아웃:

* 좌측: Primary vertical nav
* 중앙: Main dashboard / chart / list
* 우측: detail / signal / position / risk summary panel

## Grid Recommendation

```txt
app max width: 1440 ~ 1600px
outer padding: 24px
main grid gap: 16px
```

예시 12-column:

* Left rail: 80px
* Main content: 7~8 columns
* Right panel: 3~4 columns

---

# 8. Component System

## 8-1. App Shell

### Sidebar

특징:

* 어두운 캡슐형 컨테이너
* 활성 아이콘만 네온 그린 배경 또는 하이라이트
* 비활성은 아이콘만 회색/딤 처리

토큰:

* background: `bg.sidebar`
* active background: `brand.primary`
* active icon: `text.inverse`
* inactive icon: `text.tertiary`

규칙:

* 아이콘 버튼 크기: `40~44px`
* 선택 상태는 “채워진 원형/rounded-square” 사용
* hover는 채우기보다 은은한 배경 강조

---

## 8-2. Top Bar

구성:

* 페이지 제목 또는 현재 워크스페이스 이름
* 전역 검색 또는 command palette entry
* mode / session status chip
* 알림 또는 최근 이벤트 진입점
* 빠른 액션 버튼(refresh, compare, save view 등)

규칙:

* 페이지 제목과 상태칩은 왼쪽 그룹으로 묶는다
* 검색/command entry가 가장 길게 간다
* 오른쪽 액션은 아이콘 + compact chip 형태로 정리한다
* `LIVE`, degraded, reconnecting 상태는 semantic chip으로 표시하고 브랜드 그린과 혼용하지 않는다

---

## 8-3. Card

이 UI의 핵심 컴포넌트입니다.

### Base Card

```txt
background: bg.surface-1
border: 1px solid border.default
radius: radius.xl
shadow: glow.panel
padding: 16~20px
```

### Accent Card

핵심 KPI, 활성 세션, 선택된 요약 카드 등에 사용

```txt
border: 1px solid rgba(34,231,107,0.35)
shadow: glow.green.md
background: linear-gradient(180deg, rgba(34,231,107,0.04), rgba(255,255,255,0.01))
```

---

## 8-4. Button

### Primary Button

* 배경: `brand.primary`
* 텍스트: `text.inverse`
* hover: `brand.primary-2`
* active: 약간 더 어둡게
* radius: `12px`
* 높이: `40~48px`

### Secondary Button

* 배경: `bg.surface-2`
* border: `border.default`
* 텍스트: `text.primary`

### Ghost Button

* 배경 없음
* hover 시 `brand.primary-soft`

### Danger Button

* 배경: `danger`
* 텍스트: 흰색 또는 inverse

---

## 8-5. Input / Field

이 화면의 입력창은 매우 어두운 배경 + 얇은 외곽선 구조입니다.

```txt
height: 40~44px
background: bg.input
border: 1px solid border.soft
text: text.primary
placeholder: text.tertiary
radius: 10~12px
```

상태:

* focus: `border-accent + green glow`
* error: danger border
* disabled: 낮은 contrast

---

## 8-6. Tabs / Segmented Control

이미지에서 많이 보이는 형태입니다.

* 배경: `bg.surface-2`
* 활성 탭: `brand.primary`
* 비활성 탭: `text.tertiary`
* radius: pill 또는 10px
* 높이: 28~36px

예:

* Candle / Line
* 1D / 7D / 1M / 3M / 1Y
* Long / Short
* Market / Limit / Stop

---

## 8-7. Data Table

트레이딩 UI 특성상 테이블은 매우 중요합니다.

### Table Rules

* 행 높이: 36~44px
* 헤더: `text.tertiary`, 12px
* 바디: `text.secondary`, 숫자는 monospaced 추천
* hover row: `rgba(255,255,255,0.02)`
* 상승 수치: `success`
* 하락 수치: `danger`

### Signal / Position / Order Tables

* 수익/손실, blocked, retry, degraded 같은 상태는 semantic chip 또는 icon으로 표시
* tint는 셀 단위 또는 badge 단위로만 제한적으로 사용
* 진행률/깊이감 바가 필요하면 숫자 가독성을 해치지 않는 얇은 배경 레이어로 처리

---

## 8-8. Status Chip / Tag

```txt
size-sm: 24px height
size-md: 28px height
padding-x: 10~12px
radius: pill
```

예시:

* Open
* Completed
* Long
* Short
* Isolated
* Cross

색상:

* success chip
* danger chip
* neutral chip
* info chip

---

## 8-9. Chart Container

차트 자체는 가장 중요한 컴포넌트이므로 주변 UI가 과하면 안 됩니다.

규칙:

* 차트 배경은 카드와 거의 동일
* grid line은 아주 약하게
* 툴팁은 다크 카드 형태
* crosshair line은 accent 기반
* 차트 위 필터/툴바는 compact segmented control

---

# 9. Iconography

스타일상 아이콘은 아래 기준이 맞습니다.

* outline 기반
* 1.5px ~ 1.75px stroke
* 지나치게 장식적이지 않음
* 금융/대시보드에 적합한 미니멀 스타일

권장 세트:

* Lucide
* Remix Icon
* Hugeicons
* Tabler Icons

아이콘 크기:

* nav: 20~22px
* action button: 16~18px
* inline status: 12~14px

---

# 10. Motion

이 UI는 애니메이션이 과하면 싸보일 수 있습니다.
반응은 빠르고 짧아야 합니다.

## Motion Rules

* hover: 120ms ~ 160ms
* panel/toggle: 180ms ~ 220ms
* modal/sheet: 220ms ~ 260ms
* easing: `cubic-bezier(0.2, 0.8, 0.2, 1)`

효과:

* opacity
* translateY(2~6px)
* glow intensity change
* scale은 0.98 ~ 1 정도만 아주 약하게

---

# 11. Semantic Usage Rules

## Accent Green 사용 원칙

초록색이 많아 보이지만, 사실은 제한적으로 써야 고급스럽습니다.

초록색을 써야 하는 곳:

* Primary CTA
* 활성 탭
* 선택된 카드
* 상승 데이터
* 실시간 강조값
* 차트 메인 라인

초록색을 남발하면 안 되는 곳:

* 모든 제목
* 모든 아이콘
* 모든 보더
* 모든 카드 배경

즉, 전체 화면의 80%는 어두운 중립색,
15%는 화이트/그레이 텍스트,
5% 이내만 네온 포인트가 적당합니다.

---

# 12. 디자인 토큰 예시

실무에서 바로 쓰기 쉽도록 CSS 변수 형태로 정리하면 아래와 같습니다.

```css
:root {
  --bg-canvas: #0E0E10;
  --bg-app: #121119;
  --bg-surface-1: #17161F;
  --bg-surface-2: #1D1B26;
  --bg-surface-3: #24222D;
  --bg-input: #1A1822;
  --bg-sidebar: #15141C;

  --text-primary: #F5F7FA;
  --text-secondary: #B7BDC8;
  --text-tertiary: #7E8594;
  --text-disabled: #5A606C;
  --text-inverse: #0F1115;

  --brand-primary: #22E76B;
  --brand-primary-hover: #18C95B;
  --brand-primary-soft: rgba(34, 231, 107, 0.14);
  --brand-primary-glow: rgba(34, 231, 107, 0.28);

  --border-default: rgba(255, 255, 255, 0.08);
  --border-soft: rgba(255, 255, 255, 0.05);
  --border-strong: rgba(255, 255, 255, 0.12);
  --border-accent: rgba(34, 231, 107, 0.45);

  --success: #22E76B;
  --danger: #FF5A5F;
  --warning: #F5B942;
  --info: #4DA3FF;

  --radius-sm: 10px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;

  --shadow-panel:
    0 0 0 1px rgba(255,255,255,0.05),
    inset 0 1px 0 rgba(255,255,255,0.03);

  --shadow-green:
    0 0 0 1px rgba(34,231,107,0.32),
    0 0 24px rgba(34,231,107,0.18);

  --space-4: 4px;
  --space-8: 8px;
  --space-12: 12px;
  --space-16: 16px;
  --space-20: 20px;
  --space-24: 24px;
}
```

---

# 13. 컴포넌트 스타일 가이드 요약

## 카드

* 항상 둥근 모서리
* 얇은 보더
* 플랫하지 않은 미세한 깊이감
* 주요 카드만 accent glow 허용

## 버튼

* primary는 형광 그린
* secondary는 다크 서피스
* 텍스트 버튼은 최소화

## 차트

* UI보다 데이터가 주인공
* 그리드/축/툴팁 모두 저채도
* 메인 라인과 포인트만 강하게

## 표

* 숫자 정렬 일관성 중요
* bid/ask 색상 대비 명확
* 지나친 보더 사용 금지

## 내비게이션

* 좌측은 조용하게
* active만 확실하게
* 아이콘 스타일 통일

---

# 14. Figma 스타일 네이밍 제안

## Color Styles

```txt
Color/Background/Canvas
Color/Background/Surface-1
Color/Background/Surface-2
Color/Background/Input
Color/Text/Primary
Color/Text/Secondary
Color/Text/Tertiary
Color/Brand/Primary
Color/Brand/Primary-Soft
Color/Status/Success
Color/Status/Danger
Color/Border/Default
Color/Border/Accent
```

## Effect Styles

```txt
Effect/Panel/Base
Effect/Glow/Green-S
Effect/Glow/Green-M
Effect/Shadow/Soft
```

## Text Styles

```txt
Text/Display/LG
Text/Title/MD
Text/Body/MD
Text/Body/SM
Text/Caption/LG
Text/Micro
```

---

# 15. 이 스타일을 실제 서비스용으로 다듬을 때 보완할 점

첨부 시안은 매우 멋있지만, 실서비스로 가려면 아래 보완이 필요합니다.

* 대비 접근성 점검
* 텍스트 크기 최소 기준 확정
* 테이블 숫자 정렬 규칙 고정
* 입력창 에러/포커스/비활성 상태 정의 추가
* 모바일/태블릿 대응용 반응형 규칙 별도 정리
* 차트 라이브러리별 토큰 매핑
* 라이트 모드 제공 여부 결정

---

# 16. 추천 컴포넌트 목록

이 디자인 시스템으로 최소한 아래 컴포넌트까지 정의하면 실무에서 강합니다.

* AppShell
* SidebarNav
* TopBar
* SearchField
* MetricCard
* SummaryCard
* ChartCard
* SessionSelector
* OrderPanel
* SegmentedControl
* StatusChip
* DataTable
* FilterBar
* SignalFeedList
* ValidationPanel
* DiffPreviewPanel

---

# 17. 화면별 적용 매핑

## 17-1. Dashboard
- 기본 구조: page header + status bar + KPI card row + risk panel + recent signal feed
- 권장 컴포넌트: `AppShell`, `TopBar`, `MetricCard`, `StatusChip`, `DataTable`
- 스타일 원칙:
  - KPI 카드만 선택적으로 accent glow 허용
  - 리스크/경고 패널은 `warning`/`danger` semantic color만 사용
  - 최근 신호 피드는 카드 안의 dense table/list 패턴으로 처리

## 17-2. Monitoring
- 기본 구조: 좌측 세션 패널 + 중앙 chart panel + 우측 signal/position/order panel + 하단 detail tabs
- 권장 컴포넌트: `SidebarNav`, `ChartCard`, `SegmentedControl`, `StatusChip`, `DataTable`
- 스타일 원칙:
  - 중앙 차트가 시각적 주인공이며 가장 큰 면적을 차지해야 한다
  - 선택된 세션과 활성 심볼만 accent 표현을 사용한다
  - LIVE, PAPER, degraded 상태는 semantic chip으로 구분하고 브랜드 그린과 혼용하지 않는다

## 17-3. Strategies
- 목록 화면은 filter bar + dense table 중심으로 구성한다.
- 상세 화면은 summary card, JSON preview, history, notes를 수직 섹션으로 정리한다.
- 편집 화면은 긴 form을 card 묶음보다 section/tabs 흐름으로 다루고, 저장 CTA는 우측 상단 또는 하단 고정 액션으로 통일한다.

## 17-4. Backtests / Compare
- 백테스트는 run form, result summary, equity chart, trade table의 위계를 분명히 둔다.
- 비교 화면은 세션별 카드보다 공통 기준 표와 비교 차트를 우선한다.
- 성과 지표는 tabular numeric과 semantic up/down color를 함께 사용한다.

## 17-5. Logs / Settings
- 로그 화면은 검색/필터 바 + dense table + detail drawer 패턴을 사용한다.
- 설정 화면은 section title, helper text, form group, save action의 리듬을 유지한다.
- 설정/로그 화면은 glow를 최소화하고 surface와 spacing으로 품질을 만든다.
