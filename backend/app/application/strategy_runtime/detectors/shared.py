from __future__ import annotations

from app.domain.entities.market import CandleState


def candle_body_metrics(candle: CandleState) -> tuple[float, float, float]:
    candle_range = max(candle.high - candle.low, 0.0)
    if candle_range <= 0:
        return 0.0, 0.0, 0.0
    body_size = abs(candle.close - candle.open)
    body_ratio = body_size / candle_range
    body_pct = body_size / max(abs(candle.open), 1e-9)
    return candle_range, body_ratio, body_pct


def is_strong_directional_candle(
    candle: CandleState,
    *,
    direction: str,
    body_ratio_threshold: float,
    body_pct_threshold: float,
) -> tuple[bool, float, float]:
    if direction == "bullish" and candle.close <= candle.open:
        return False, 0.0, 0.0
    if direction == "bearish" and candle.close >= candle.open:
        return False, 0.0, 0.0

    _, body_ratio, body_pct = candle_body_metrics(candle)
    matched = body_ratio >= body_ratio_threshold and body_pct >= body_pct_threshold
    return matched, body_ratio, body_pct


def true_range(candle: CandleState, prev_close: float | None) -> float:
    candle_range = max(candle.high - candle.low, 0.0)
    if prev_close is None:
        return candle_range
    return max(candle_range, abs(candle.high - prev_close), abs(candle.low - prev_close))


def average_true_range(candles: list[CandleState], period: int) -> list[float | None]:
    atr: list[float | None] = [None] * len(candles)
    if period <= 0:
        return atr

    tr_values: list[float] = []
    prev_close: float | None = None
    for index, candle in enumerate(candles):
        tr_values.append(true_range(candle, prev_close))
        prev_close = candle.close
        if index >= period - 1:
            window = tr_values[index - period + 1 : index + 1]
            atr[index] = sum(window) / len(window)
    return atr


def is_confirmation_candle(candle: CandleState, *, direction: str = "bullish") -> bool:
    candle_range = max(candle.high - candle.low, 0.0)
    if candle_range <= 0:
        return False

    body_ratio = abs(candle.close - candle.open) / candle_range
    if direction == "bullish":
        if candle.close <= candle.open:
            return False
        close_position = (candle.close - candle.low) / candle_range
        return close_position >= 0.6 and body_ratio >= 0.45

    if direction == "bearish":
        if candle.close >= candle.open:
            return False
        close_position = (candle.high - candle.close) / candle_range
        return close_position >= 0.6 and body_ratio >= 0.45

    raise ValueError(f"unsupported direction: {direction}")


def zone_retested(
    candle: CandleState,
    *,
    lower: float,
    upper: float,
    tolerance_pct: float,
    direction: str,
) -> bool:
    if direction == "bullish":
        return candle.low <= upper * (1.0 + tolerance_pct) and candle.high >= lower
    if direction == "bearish":
        return candle.high >= lower * (1.0 - tolerance_pct) and candle.low <= upper
    raise ValueError(f"unsupported direction: {direction}")
