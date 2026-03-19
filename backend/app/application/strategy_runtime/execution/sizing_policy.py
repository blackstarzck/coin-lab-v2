from __future__ import annotations

from app.domain.entities.market import MarketSnapshot
from app.domain.entities.session import Signal
from app.domain.strategy_runtime import PositionPlan


DEFAULT_INITIAL_CAPITAL = 1_000_000.0
DEFAULT_POSITION_SIZE_MODE = "fixed_percent"
DEFAULT_POSITION_SIZE_VALUE = 0.1


class PositionSizingPolicy:
    def calculate_quantity(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        signal: Signal | None = None,
    ) -> float:
        return self.build_position_plan(strategy_config, snapshot, signal).expected_qty

    def build_position_plan(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        signal: Signal | None = None,
    ) -> PositionPlan:
        price = snapshot.latest_price or 0.0
        if price <= 0:
            return PositionPlan(
                size_mode="invalid_price",
                notional_krw=0.0,
                expected_qty=0.0,
                initial_stop_loss=self._runtime_stop_loss(signal),
                initial_take_profit=self._runtime_take_profit(signal),
            )

        pos_cfg = self._as_dict(strategy_config.get("position"))
        size_mode = str(pos_cfg.get("size_mode", DEFAULT_POSITION_SIZE_MODE))
        size_value = self._as_float(pos_cfg.get("size_value"), DEFAULT_POSITION_SIZE_VALUE)
        initial_capital = self._as_float(
            self._as_dict(strategy_config.get("backtest")).get("initial_capital"),
            DEFAULT_INITIAL_CAPITAL,
        )
        stop_loss_price = self._runtime_stop_loss(signal) or self._fallback_stop_loss(strategy_config, price)
        take_profit_price = self._runtime_take_profit(signal) or self._fallback_take_profit(strategy_config, price)

        qty = 0.0
        notional = 0.0
        if size_mode == "fixed_qty":
            qty = max(size_value, 0.0)
            notional = qty * price
        elif size_mode == "fixed_amount":
            notional = max(size_value, 0.0)
            qty = notional / price if price > 0 else 0.0
        elif size_mode == "fixed_percent":
            notional = initial_capital * max(size_value, 0.0)
            qty = notional / price
        elif size_mode == "fractional_kelly":
            notional = initial_capital * max(min(size_value, 1.0), 0.0)
            qty = notional / price
        elif size_mode == "risk_per_trade":
            risk_budget = initial_capital * max(size_value, 0.0)
            stop_distance = max(price - (stop_loss_price or price), 0.0)
            qty = (risk_budget / stop_distance) if stop_distance > 0 else 0.0
            notional = qty * price

        qty, notional = self._apply_size_caps(pos_cfg, qty, notional, initial_capital, price)
        return PositionPlan(
            size_mode=size_mode,
            notional_krw=notional,
            expected_qty=max(qty, 0.0),
            initial_stop_loss=stop_loss_price,
            initial_take_profit=take_profit_price,
            partial_take_profits=self._partial_take_profits(strategy_config, price),
            trailing_stop_pct=self._as_float(self._as_dict(strategy_config.get("exit")).get("trailing_stop_pct"), 0.0) or None,
        )

    def _apply_size_caps(
        self,
        pos_cfg: dict[str, object],
        qty: float,
        notional: float,
        initial_capital: float,
        price: float,
    ) -> tuple[float, float]:
        size_caps = self._as_dict(pos_cfg.get("size_caps"))
        min_pct = self._as_float(size_caps.get("min_pct"), 0.0)
        max_pct = self._as_float(size_caps.get("max_pct"), 1.0)
        if initial_capital <= 0 or price <= 0:
            return qty, notional
        min_notional = initial_capital * min_pct if min_pct > 0 else 0.0
        max_notional = initial_capital * max_pct if max_pct > 0 else None

        adjusted_notional = max(notional, min_notional)
        if max_notional is not None:
            adjusted_notional = min(adjusted_notional, max_notional)
        adjusted_qty = adjusted_notional / price if price > 0 else 0.0
        return adjusted_qty, adjusted_notional

    def _partial_take_profits(self, strategy_config: dict[str, object], price: float) -> tuple[tuple[float, float], ...]:
        exit_cfg = self._as_dict(strategy_config.get("exit"))
        partials = exit_cfg.get("partial_take_profits")
        if not isinstance(partials, list):
            return ()
        plans: list[tuple[float, float]] = []
        for item in partials:
            if not isinstance(item, dict):
                continue
            target_pct = self._as_float(item.get("at_profit_pct"), self._as_float(item.get("target_pct"), 0.0))
            close_ratio = self._as_float(item.get("close_ratio"), 0.0)
            if target_pct <= 0 or close_ratio <= 0:
                continue
            plans.append((price * (1.0 + target_pct), close_ratio))
        return tuple(plans)

    def _runtime_stop_loss(self, signal: Signal | None) -> float | None:
        runtime = self._runtime_context(signal)
        entry_setup = runtime.get("entry_setup")
        if not isinstance(entry_setup, dict):
            return None
        risk = entry_setup.get("risk")
        if isinstance(risk, dict) and isinstance(risk.get("stop_loss_price"), int | float):
            return float(risk["stop_loss_price"])
        if isinstance(entry_setup.get("invalidation_price"), int | float):
            return float(entry_setup["invalidation_price"])
        return None

    def _runtime_take_profit(self, signal: Signal | None) -> float | None:
        runtime = self._runtime_context(signal)
        entry_setup = runtime.get("entry_setup")
        if not isinstance(entry_setup, dict):
            return None
        risk = entry_setup.get("risk")
        if isinstance(risk, dict):
            prices = risk.get("take_profit_prices")
            if isinstance(prices, list) and prices and isinstance(prices[0], int | float):
                return float(prices[0])
        return None

    def _runtime_context(self, signal: Signal | None) -> dict[str, object]:
        if signal is None or not isinstance(signal.explain_payload, dict):
            return {}
        runtime = signal.explain_payload.get("strategy_runtime")
        return runtime if isinstance(runtime, dict) else {}

    def _fallback_stop_loss(self, strategy_config: dict[str, object], price: float) -> float | None:
        stop_pct = self._as_float(self._as_dict(strategy_config.get("exit")).get("stop_loss_pct"), 0.0)
        return price * (1.0 - stop_pct) if stop_pct > 0 else None

    def _fallback_take_profit(self, strategy_config: dict[str, object], price: float) -> float | None:
        tp_pct = self._as_float(self._as_dict(strategy_config.get("exit")).get("take_profit_pct"), 0.0)
        return price * (1.0 + tp_pct) if tp_pct > 0 else None

    def _as_dict(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback
