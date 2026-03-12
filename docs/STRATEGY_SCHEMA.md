# STRATEGY_SCHEMA.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 전략 타입
- dsl
- plugin
- hybrid

## 권장 최상위 구조
```json
{
  "id": "btc_breakout_v1",
  "name": "BTC Breakout V1",
  "type": "dsl",
  "description": "5분봉 EMA + 돌파 전략",
  "market": {},
  "universe": {},
  "entry": {},
  "reentry": {},
  "position": {},
  "exit": {},
  "risk": {},
  "execution": {},
  "backtest": {},
  "labels": [],
  "notes": ""
}
```

## market
- exchange
- market_types
- timeframes
- trade_basis: candle | tick | hybrid

## universe
- mode: dynamic
- sources: top_volume, surge, watchlist
- max_symbols
- refresh_sec

## entry condition 예시
- indicator_compare
- threshold_compare
- cross_over
- cross_under
- price_breakout
- volume_spike
- rsi_range
- candle_pattern
- regime_match

## position
- max_open_positions_per_symbol
- allow_scale_in
- size_mode: fixed_amount | fixed_percent | fractional_kelly | risk_per_trade
- size_caps
- max_concurrent_positions

## exit
- stop_loss_pct
- take_profit_pct
- trailing_stop_pct
- time_stop

## risk
- daily_loss_limit_pct
- max_strategy_drawdown_pct
- prevent_duplicate_entry
- max_order_retries
- kill_switch_enabled

## execution
- entry_order_type
- exit_order_type
- limit_timeout_sec
- fallback_to_market
- slippage_model
- fee_model

## backtest
- initial_capital
- fee_bps
- slippage_bps
- latency_ms
- fill_assumption

## Python Plugin 계약
```python
class StrategyPlugin:
    plugin_id: str
    def validate(self, config: dict) -> None: ...
    def evaluate(self, snapshot: "StrategySnapshot") -> "StrategyDecision": ...
    def explain(self, snapshot: "StrategySnapshot") -> dict: ...
```

## 버전 규칙
- strategy는 mutable
- strategy_version은 immutable
- 실행은 strategy_version_id 기준
- 백테스트/라이브 세션은 사용 버전을 반드시 기록
