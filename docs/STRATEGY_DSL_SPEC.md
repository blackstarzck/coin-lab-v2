# STRATEGY_DSL_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 전략 JSON DSL의 유일한 명세 문서다.  
프론트의 전략 편집기, 백엔드 validator, Python evaluator, 저장 스키마는 모두 이 문서를 SSOT로 따른다.

참조:
- 실행 규칙: [EXECUTION_SIMULATION_SPEC.md](./EXECUTION_SIMULATION_SPEC.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

---

## 2. 설계 목표
- 사람이 읽기 쉬운 JSON
- 폼 UI와 1:1 매핑 가능
- validator/evaluator 구현 가능
- explain/debug 출력 가능
- Python plugin으로 확장 가능

---

## 3. 전략 타입
- `dsl`: 전부 JSON DSL로 평가
- `plugin`: 핵심 로직은 Python plugin이 평가
- `hybrid`: universe/risk/execution 등은 DSL, 핵심 entry/exit 일부는 plugin 또는 plugin helper 사용

---

## 4. 최상위 스키마

```json
{
  "id": "btc_breakout_v1",
  "name": "BTC Breakout V1",
  "type": "dsl",
  "schema_version": "1.0.0",
  "description": "5분봉 EMA + 돌파 전략",
  "enabled": true,
  "market": {},
  "universe": {},
  "entry": {},
  "reentry": {},
  "position": {},
  "exit": {},
  "risk": {},
  "execution": {},
  "backtest": {},
  "labels": ["trend", "breakout"],
  "notes": "초기 실험 버전"
}
```

### 필수 필드
- `id`
- `name`
- `type`
- `schema_version`
- `market`
- `universe`
- `entry`
- `position`
- `exit`
- `risk`
- `execution`
- `backtest`

### Root object note
- The DSL root is the canonical shared shape for TypeScript, Pydantic, and DB `config_json`.
- The root object does not introduce a nested `meta` wrapper.

### 금지
- 최상위 unknown key
- snake_case와 camelCase 혼용
- 문서에 없는 operator 타입

---

## 5. 공통 값 타입

### 5.1 SourceRef
```json
{ "kind": "price", "field": "close" }
```

허용 `kind`:
- `price`
- `indicator`
- `derived`
- `constant`

예시:
```json
{ "kind": "indicator", "name": "ema", "params": { "length": 20 } }
{ "kind": "constant", "value": 70 }
```

### 5.2 TimeframeRef
```json
{ "base": "5m" }
```

또는 cross-timeframe:
```json
{ "base": "5m", "compare_to": "15m" }
```

규칙:
- `compare_to`는 `market.timeframes`에 포함되어야 한다
- base timeframe 기준 snapshot에서 필요한 상위 timeframe 값이 미존재하면 evaluation은 `NOT_READY`

### 5.3 ValueRef
- `price.close`
- `price.open`
- `indicator.ema(20)`
- `derived.highest_high(20)`
- `constant(0.03)`

UI/저장에서는 구조화 object를 사용하고, 설명 예시에서만 문자열 shorthand를 쓸 수 있다.

---

## 6. market 섹션

```json
{
  "exchange": "UPBIT",
  "market_types": ["KRW", "BTC", "USDT"],
  "timeframes": ["1m", "5m", "15m"],
  "trade_basis": "hybrid",
  "trigger": "ON_CANDLE_CLOSE"
}
```

### 규칙
- `exchange`: 현재 `UPBIT`만 허용
- `trade_basis`: `candle | tick | hybrid`
- `trigger`: `ON_TICK_BATCH | ON_CANDLE_CLOSE | ON_CANDLE_UPDATE | ON_MANUAL_REEVALUATE`
- `timeframes`: 중복 금지
- `tick` 전용 전략이어도 최소 한 개의 candle timeframe을 가질 수 있다
- `trigger`를 생략하면 기본값은 `ON_CANDLE_CLOSE`

---

## 7. universe 섹션

```json
{
  "mode": "dynamic",
  "sources": ["top_turnover", "surge", "watchlist"],
  "max_symbols": 10,
  "refresh_sec": 60,
  "filters": {
    "min_24h_turnover_krw": 1000000000,
    "exclude_symbols": ["KRW-BTT"]
  }
}
```

### 허용 sources
- `top_turnover`
- `top_volume`
- `surge`
- `drop`
- `watchlist`

### 규칙
- 현재 프로젝트는 종목 독립형 전략이므로 universe는 **실행 후보군 생성**만 담당한다
- universe가 생성한 종목별로 동일 전략 인스턴스가 독립 평가된다

---

## 8. logical block 규칙

모든 condition block은 아래 4개 중 하나다.
- `all`
- `any`
- `not`
- `leaf`

### 8.1 all
```json
{
  "logic": "all",
  "conditions": [ ... ]
}
```
- 모든 하위 조건이 `true`여야 한다
- 빈 배열 금지

### 8.2 any
```json
{
  "logic": "any",
  "conditions": [ ... ]
}
```
- 하나 이상 `true`

### 8.3 not
```json
{
  "logic": "not",
  "condition": { ... }
}
```
- 단일 하위 조건만 허용

### 8.4 leaf
```json
{
  "type": "indicator_compare",
  ...
}
```

---

## 9. leaf operator 목록

## 9.1 indicator_compare
```json
{
  "type": "indicator_compare",
  "left": { "kind": "indicator", "name": "ema", "params": { "length": 20 } },
  "operator": ">",
  "right": { "kind": "indicator", "name": "ema", "params": { "length": 50 } }
}
```

### 허용 operator
- `>`
- `>=`
- `<`
- `<=`
- `==`
- `!=`

---

## 9.2 threshold_compare
```json
{
  "type": "threshold_compare",
  "left": { "kind": "indicator", "name": "rsi", "params": { "length": 14 } },
  "operator": "<=",
  "right": { "kind": "constant", "value": 30 }
}
```

---

## 9.3 cross_over
```json
{
  "type": "cross_over",
  "left": { "kind": "price", "field": "close" },
  "right": { "kind": "indicator", "name": "ema", "params": { "length": 20 } },
  "lookback_bars": 1
}
```

규칙:
- 직전 bar와 현재 bar 비교 기준
- `lookback_bars`는 기본값 1
- 같은 시점에 두 번 true를 내지 않도록 snapshot key를 사용

---

## 9.4 cross_under
구조는 `cross_over`와 동일, 방향만 반대

---

## 9.5 price_breakout
```json
{
  "type": "price_breakout",
  "source": { "kind": "price", "field": "close" },
  "operator": ">",
  "reference": {
    "kind": "derived",
    "name": "highest_high",
    "params": { "lookback": 20, "exclude_current": true }
  }
}
```

---

## 9.6 volume_spike
```json
{
  "type": "volume_spike",
  "source": { "kind": "derived", "name": "volume_ratio", "params": { "lookback": 20 } },
  "operator": ">=",
  "threshold": 2.0
}
```

---

## 9.7 rsi_range
```json
{
  "type": "rsi_range",
  "source": { "kind": "indicator", "name": "rsi", "params": { "length": 14 } },
  "min": 45,
  "max": 65
}
```

규칙:
- `min <= max`
- 둘 다 inclusive

---

## 9.8 candle_pattern
```json
{
  "type": "candle_pattern",
  "pattern": "bullish_engulfing",
  "timeframe": "5m"
}
```

허용 pattern 예시:
- `bullish_engulfing`
- `bearish_engulfing`
- `inside_bar_break`
- `long_lower_wick`

---

## 9.9 regime_match
```json
{
  "type": "regime_match",
  "regime": "trend_up"
}
```

허용 regime:
- `trend_up`
- `trend_down`
- `range`
- `high_volatility`
- `low_volatility`

---

## 10. entry 섹션

```json
{
  "logic": "all",
  "conditions": [
    {
      "type": "indicator_compare",
      "left": { "kind": "indicator", "name": "ema", "params": { "length": 20 } },
      "operator": ">",
      "right": { "kind": "indicator", "name": "ema", "params": { "length": 50 } }
    },
    {
      "type": "price_breakout",
      "source": { "kind": "price", "field": "close" },
      "operator": ">",
      "reference": {
        "kind": "derived",
        "name": "highest_high",
        "params": { "lookback": 20, "exclude_current": true }
      }
    }
  ]
}
```

### 평가 결과
entry evaluator는 아래를 생성한다.
```json
{
  "decision": "ENTER" ,
  "confidence": 0.78,
  "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
  "explain": {
    "matched_conditions": ["c1", "c2"],
    "failed_conditions": []
  }
}
```

---

## 11. reentry 섹션

```json
{
  "allow": false,
  "cooldown_bars": 3,
  "require_reset": true,
  "reset_condition": {
    "type": "threshold_compare",
    "left": { "kind": "price", "field": "close" },
    "operator": "<",
    "right": {
      "kind": "derived",
      "name": "highest_high",
      "params": { "lookback": 20 }
    }
  }
}
```

규칙:
- `allow=false`면 나머지 필드는 무시 가능
- `cooldown_bars`는 0 이상
- reset_condition 평가 전까지 동일 방향 재진입 금지 가능
- 런타임은 청산 직후 동일 심볼의 reentry guard를 시작한다.
- `cooldown_bars > 0`이면 먼저 cooldown을 소진하고, `require_reset=true`이면 이후 `reset_condition`이 true가 될 때까지 진입을 차단한다.

---

## 12. position 섹션

```json
{
  "max_open_positions_per_symbol": 1,
  "allow_scale_in": false,
  "size_mode": "fractional_kelly",
  "size_value": 0.25,
  "size_caps": {
    "min_pct": 0.02,
    "max_pct": 0.1
  },
  "max_concurrent_positions": 4
}
```

### size_mode
- `fixed_amount`
- `fixed_percent`
- `fractional_kelly`
- `risk_per_trade`

규칙:
- `fractional_kelly`일 때 `size_value`는 0~1
- `max_open_positions_per_symbol` 현재 권장값은 1

---

## 13. exit 섹션

```json
{
  "stop_loss_pct": 0.015,
  "take_profit_pct": 0.03,
  "trailing_stop_pct": 0.01,
  "time_stop_bars": 12,
  "partial_take_profits": [
    { "at_profit_pct": 0.02, "close_ratio": 0.5 }
  ]
}
```

규칙:
- `stop_loss_pct`, `take_profit_pct`, `trailing_stop_pct`는 양수
- `partial_take_profits.close_ratio` 합은 1.0 이하
- trailing stop은 unrealized high-watermark 기준

---

## 14. risk 섹션

```json
{
  "daily_loss_limit_pct": 0.03,
  "max_strategy_drawdown_pct": 0.1,
  "prevent_duplicate_entry": true,
  "max_order_retries": 2,
  "kill_switch_enabled": true
}
```

규칙:
- 리스크 차단은 entry보다 우선
- `prevent_duplicate_entry=true`면 동일 dedupe key entry 거부
- kill switch 발동 시 신규 진입은 차단되고, 세션은 `STOPPING` 전이 + risk event 기록으로 종료 흐름에 들어간다

---

## 15. execution 섹션

```json
{
  "entry_order_type": "limit",
  "exit_order_type": "limit",
  "limit_timeout_sec": 15,
  "fallback_to_market": true,
  "slippage_model": "fixed_bps",
  "fee_model": "per_fill"
}
```

허용값:
- `entry_order_type`: `market | limit`
- `exit_order_type`: `market | limit`
- `slippage_model`: `none | fixed_bps | volatility_scaled`
- `fee_model`: `per_fill | per_order`

---

## 16. backtest 섹션

```json
{
  "initial_capital": 1000000,
  "fee_bps": 5,
  "slippage_bps": 3,
  "latency_ms": 200,
  "fill_assumption": "mid"
}
```

허용 `fill_assumption`:
- `best_bid_ask`
- `mid`
- `next_tick`
- `next_bar_open`

---

## 17. explain payload 표준

```json
{
  "snapshot_key": "KRW-BTC|5m|2026-03-10T00:15:00Z",
  "decision": "ENTER",
  "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
  "facts": [
    { "label": "ema20", "value": 142000000.0 },
    { "label": "ema50", "value": 141800000.0 }
  ],
  "matched_conditions": ["entry.conditions[0]", "entry.conditions[1]"],
  "failed_conditions": [],
  "risk_blocks": []
}
```

---

## 18. validator 규칙

### 실패 코드 예시
- `DSL_UNKNOWN_TOP_LEVEL_KEY`
- `DSL_UNKNOWN_OPERATOR`
- `DSL_INVALID_ENUM`
- `DSL_MISSING_REQUIRED_FIELD`
- `DSL_INVALID_THRESHOLD_RANGE`
- `DSL_INVALID_TIMEFRAME_REFERENCE`
- `DSL_INVALID_PARTIAL_TP_SUM`
- `DSL_PLUGIN_AND_DSL_CONFLICT`

### validator 요구사항
- unknown field 차단
- enum strict match
- 수치 범위 확인
- cross-timeframe 참조 유효성 확인
- partial_take_profits 합계 확인
- nested condition tree 최대 깊이 제한 가능

---

## 19. plugin 계약

```python
class StrategyPlugin:
    plugin_id: str
    plugin_version: str

    def validate(self, config: dict) -> None: ...
    def evaluate(self, snapshot: "StrategySnapshot") -> "StrategyDecision": ...
    def explain(self, snapshot: "StrategySnapshot") -> dict: ...
```

### hybrid 규칙
- plugin이 entry만 대체하는지, exit만 대체하는지 명시해야 한다
- 동일 영역(entry/exit)을 DSL과 plugin이 동시에 authoritative하게 결정할 수 없다
- plugin helper는 derived value provider 역할만 허용 가능

---

## 20. 샘플 전략

```json
{
  "id": "btc_breakout_v1",
  "name": "BTC Breakout V1",
  "type": "dsl",
  "schema_version": "1.0.0",
  "description": "5분봉 EMA + 돌파 전략",
  "enabled": true,
  "market": {
    "exchange": "UPBIT",
    "market_types": ["KRW"],
    "timeframes": ["5m", "15m"],
    "trade_basis": "candle"
  },
  "universe": {
    "mode": "dynamic",
    "sources": ["top_turnover", "watchlist"],
    "max_symbols": 10,
    "refresh_sec": 60,
    "filters": {
      "min_24h_turnover_krw": 1000000000,
      "exclude_symbols": []
    }
  },
  "entry": {
    "logic": "all",
    "conditions": [
      {
        "type": "indicator_compare",
        "left": { "kind": "indicator", "name": "ema", "params": { "length": 20 } },
        "operator": ">",
        "right": { "kind": "indicator", "name": "ema", "params": { "length": 50 } }
      },
      {
        "type": "price_breakout",
        "source": { "kind": "price", "field": "close" },
        "operator": ">",
        "reference": {
          "kind": "derived",
          "name": "highest_high",
          "params": { "lookback": 20, "exclude_current": true }
        }
      }
    ]
  },
  "reentry": {
    "allow": false,
    "cooldown_bars": 3,
    "require_reset": true,
    "reset_condition": {
      "type": "threshold_compare",
      "left": { "kind": "price", "field": "close" },
      "operator": "<",
      "right": {
        "kind": "derived",
        "name": "highest_high",
        "params": { "lookback": 20 }
      }
    }
  },
  "position": {
    "max_open_positions_per_symbol": 1,
    "allow_scale_in": false,
    "size_mode": "fixed_percent",
    "size_value": 0.1,
    "size_caps": { "min_pct": 0.02, "max_pct": 0.1 },
    "max_concurrent_positions": 4
  },
  "exit": {
    "stop_loss_pct": 0.015,
    "take_profit_pct": 0.03
  },
  "risk": {
    "daily_loss_limit_pct": 0.03,
    "max_strategy_drawdown_pct": 0.1,
    "prevent_duplicate_entry": true,
    "max_order_retries": 2,
    "kill_switch_enabled": true
  },
  "execution": {
    "entry_order_type": "limit",
    "exit_order_type": "limit",
    "limit_timeout_sec": 15,
    "fallback_to_market": true,
    "slippage_model": "fixed_bps",
    "fee_model": "per_fill"
  },
  "backtest": {
    "initial_capital": 1000000,
    "fee_bps": 5,
    "slippage_bps": 3,
    "latency_ms": 200,
    "fill_assumption": "next_bar_open"
  },
  "labels": ["trend", "breakout"],
  "notes": ""
}
```
