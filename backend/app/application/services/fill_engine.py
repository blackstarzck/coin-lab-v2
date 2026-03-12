from __future__ import annotations

from typing import cast

from ...domain.entities.session import ExitReason, FillResult, Position


class FillEngine:
    def __init__(self) -> None:
        self._high_watermarks: dict[str, float] = {}

    def simulate_market_fill(
        self,
        base_price: float,
        side: str,
        slippage_model: str,
        slippage_bps: float,
        fee_bps: float,
        qty: float,
        volatility_ratio: float = 1.0,
    ) -> FillResult:
        fill_price = self.apply_slippage(base_price, side, slippage_model, slippage_bps, volatility_ratio)
        notional = fill_price * qty
        fee = self.calculate_fee(notional, fee_bps, "per_fill")
        slippage_amount = abs(fill_price - base_price) * qty
        return FillResult(
            filled=True,
            fill_price=fill_price,
            fill_qty=qty,
            fee_amount=fee,
            slippage_amount=slippage_amount,
        )

    def simulate_limit_fill(
        self,
        limit_price: float,
        candle_high: float,
        candle_low: float,
        side: str,
        fee_bps: float,
        qty: float,
    ) -> FillResult:
        can_fill = False
        side_upper = side.upper()
        if side_upper == "BUY":
            can_fill = candle_low <= limit_price
        elif side_upper == "SELL":
            can_fill = candle_high >= limit_price

        if not can_fill:
            return FillResult(
                filled=False,
                fill_price=None,
                fill_qty=0.0,
                fee_amount=0.0,
                slippage_amount=0.0,
            )

        notional = limit_price * qty
        fee = self.calculate_fee(notional, fee_bps, "per_fill")
        return FillResult(
            filled=True,
            fill_price=limit_price,
            fill_qty=qty,
            fee_amount=fee,
            slippage_amount=0.0,
        )

    def evaluate_exit_triggers(
        self,
        position: Position,
        current_price: float,
        candle_high: float,
        candle_low: float,
        exit_config: dict[str, object],
        bar_count: int,
    ) -> ExitReason | None:
        if bool(exit_config.get("emergency_kill", False)):
            return ExitReason.EMERGENCY_KILL

        if bool(exit_config.get("exchange_reject_safety_exit", False)):
            return ExitReason.EXCHANGE_REJECT

        conflict = self.check_intra_bar_conflict(position, candle_high, candle_low, exit_config)
        if conflict is not None:
            return conflict

        stop_price = self._get_stop_loss_price(position, exit_config)
        if stop_price is not None and current_price <= stop_price:
            return ExitReason.STOP_LOSS

        trailing_stop_pct = self._as_float(exit_config.get("trailing_stop_pct"), 0.0)
        if trailing_stop_pct > 0:
            high_watermark = self.update_high_watermark(position.id, candle_high)
            trailing_stop = self.calculate_trailing_stop(high_watermark, trailing_stop_pct)
            effective_stop = max(trailing_stop, stop_price) if stop_price is not None else trailing_stop
            if current_price <= effective_stop:
                return ExitReason.TRAILING_STOP

        take_profit_price = self._get_take_profit_price(position, exit_config)
        if take_profit_price is not None and current_price >= take_profit_price:
            return ExitReason.TAKE_PROFIT

        max_hold_bars = self._as_int(exit_config.get("time_stop_bars"), 0)
        if max_hold_bars > 0 and bar_count >= max_hold_bars:
            return ExitReason.TIME_STOP

        if bool(exit_config.get("manual_stop", False)):
            return ExitReason.MANUAL_STOP

        if bool(exit_config.get("strategy_exit", False)):
            return ExitReason.STRATEGY_EXIT

        return None

    def calculate_fee(self, notional: float, fee_bps: float, fee_model: str) -> float:
        if fee_model not in {"per_fill", "per_order"}:
            return 0.0
        return notional * fee_bps / 10000.0

    def apply_slippage(self, base_price: float, side: str, model: str, bps: float, volatility_ratio: float) -> float:
        if model == "none":
            return base_price

        effective_bps = bps
        if model == "volatility_scaled":
            effective_bps = bps * max(1.0, volatility_ratio)
        if model not in {"fixed_bps", "volatility_scaled"}:
            return base_price

        side_upper = side.upper()
        if side_upper == "BUY":
            return base_price * (1.0 + effective_bps / 10000.0)
        return base_price * (1.0 - effective_bps / 10000.0)

    def check_intra_bar_conflict(self, position: Position, candle_high: float, candle_low: float, exit_config: dict[str, object]) -> ExitReason | None:
        if position.side.upper() not in {"LONG", "BUY"}:
            return None
        stop_price = self._get_stop_loss_price(position, exit_config)
        tp_price = self._get_take_profit_price(position, exit_config)
        if stop_price is None or tp_price is None:
            return None
        stop_hit = candle_low <= stop_price
        tp_hit = candle_high >= tp_price
        if stop_hit and tp_hit:
            return ExitReason.STOP_LOSS_INTRA_BAR_CONSERVATIVE
        return None

    def update_high_watermark(self, position_id: str, current_high: float) -> float:
        prev = self._high_watermarks.get(position_id)
        if prev is None:
            self._high_watermarks[position_id] = current_high
            return current_high
        updated = max(prev, current_high)
        self._high_watermarks[position_id] = updated
        return updated

    def calculate_trailing_stop(self, high_watermark: float, trailing_stop_pct: float) -> float:
        return high_watermark * (1.0 - trailing_stop_pct)

    def process_partial_take_profits(
        self,
        position: Position,
        current_price: float,
        partial_tp_config: list[dict[str, object]],
    ) -> list[FillResult]:
        if position.avg_entry_price is None or position.quantity <= 0:
            return []

        sorted_cfg = sorted(
            partial_tp_config,
            key=lambda item: self._as_float(cast(dict[str, object], item).get("at_profit_pct"), 0.0),
        )
        remaining_qty = position.quantity
        current_profit_pct = (current_price / position.avg_entry_price) - 1.0
        fills: list[FillResult] = []

        for item in sorted_cfg:
            target_pct = self._as_float(item.get("at_profit_pct"), 0.0)
            close_ratio = self._as_float(item.get("close_ratio"), 0.0)
            if current_profit_pct < target_pct or close_ratio <= 0.0 or remaining_qty <= 0.0:
                continue
            close_qty = min(remaining_qty, position.quantity * close_ratio)
            remaining_qty -= close_qty
            fills.append(
                FillResult(
                    filled=True,
                    fill_price=current_price,
                    fill_qty=close_qty,
                    fee_amount=0.0,
                    slippage_amount=0.0,
                    exit_reason=ExitReason.TAKE_PROFIT.value,
                )
            )
        return fills

    def _get_stop_loss_price(self, position: Position, exit_config: dict[str, object]) -> float | None:
        if position.stop_loss_price is not None:
            return position.stop_loss_price
        stop_loss_pct = self._as_float(exit_config.get("stop_loss_pct"), 0.0)
        if stop_loss_pct <= 0 or position.avg_entry_price is None:
            return None
        return position.avg_entry_price * (1.0 - stop_loss_pct)

    def _get_take_profit_price(self, position: Position, exit_config: dict[str, object]) -> float | None:
        if position.take_profit_price is not None:
            return position.take_profit_price
        take_profit_pct = self._as_float(exit_config.get("take_profit_pct"), 0.0)
        if take_profit_pct <= 0 or position.avg_entry_price is None:
            return None
        return position.avg_entry_price * (1.0 + take_profit_pct)

    def _as_int(self, value: object, fallback: int) -> int:
        return int(value) if isinstance(value, int | float) else fallback

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback
