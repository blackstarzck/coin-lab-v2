from __future__ import annotations

from app.application.services.fill_engine import FillEngine
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.session import FillResult, OrderIntent, OrderType


class OrderLifecyclePolicy:
    def __init__(self, fill_engine: FillEngine) -> None:
        self.fill_engine = fill_engine

    def simulate_entry_fill(self, intent: OrderIntent, snapshot: MarketSnapshot, strategy_config: dict[str, object]) -> FillResult:
        backtest_cfg = self._as_dict(strategy_config.get("backtest"))
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        candle = self._resolve_candle(snapshot, strategy_config)
        base_price = candle["open"] if str(backtest_cfg.get("fill_assumption", "next_bar_open")) == "next_bar_open" else candle["close"]
        slippage_model = str(execution_cfg.get("slippage_model", "fixed_bps"))
        slippage_bps = self._as_float(backtest_cfg.get("slippage_bps"), 0.0)
        fee_bps = self._as_float(backtest_cfg.get("fee_bps"), 0.0)

        if intent.order_type == OrderType.MARKET.value:
            return self.fill_engine.simulate_market_fill(
                base_price=base_price,
                side=intent.side,
                slippage_model=slippage_model,
                slippage_bps=slippage_bps,
                fee_bps=fee_bps,
                qty=intent.requested_qty,
            )

        limit_price = intent.limit_price if intent.limit_price is not None else base_price
        return self.fill_engine.simulate_limit_fill(
            limit_price=limit_price,
            candle_high=candle["high"],
            candle_low=candle["low"],
            side=intent.side,
            fee_bps=fee_bps,
            qty=intent.requested_qty,
        )

    def handle_limit_timeout(self, intent: OrderIntent, strategy_config: dict[str, object], snapshot: MarketSnapshot) -> FillResult:
        if not intent.fallback_to_market:
            return FillResult(
                filled=False,
                fill_price=None,
                fill_qty=0.0,
                fee_amount=0.0,
                slippage_amount=0.0,
            )

        backtest_cfg = self._as_dict(strategy_config.get("backtest"))
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        base_price = snapshot.latest_price or 0.0
        return self.fill_engine.simulate_market_fill(
            base_price=base_price,
            side=intent.side,
            slippage_model=str(execution_cfg.get("slippage_model", "fixed_bps")),
            slippage_bps=self._as_float(backtest_cfg.get("slippage_bps"), 0.0),
            fee_bps=self._as_float(backtest_cfg.get("fee_bps"), 0.0),
            qty=intent.requested_qty,
        )

    def _resolve_candle(self, snapshot: MarketSnapshot, strategy_config: dict[str, object]) -> dict[str, float]:
        market = self._as_dict(strategy_config.get("market"))
        tf_raw = market.get("timeframes")
        timeframes = tf_raw if isinstance(tf_raw, list) else []
        timeframe = str(timeframes[0]) if timeframes else "1m"
        candle = snapshot.candles.get(timeframe)
        if candle is None:
            price = snapshot.latest_price or 0.0
            return {"open": price, "high": price, "low": price, "close": price}
        return {"open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close}

    def _as_dict(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback
