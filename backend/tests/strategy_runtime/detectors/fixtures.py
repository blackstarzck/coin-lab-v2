from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.strategy_runtime.detectors import DetectorContext
from app.domain.entities.market import CandleState, ConnectionState, MarketSnapshot


def snapshot_with_custom_candles(
    candles: list[dict[str, float]],
    *,
    symbol: str = "KRW-BTC",
    timeframe: str = "5m",
    snapshot_time: datetime | None = None,
) -> MarketSnapshot:
    now = snapshot_time or datetime.now(UTC)
    series: list[CandleState] = []
    for index, candle in enumerate(candles):
        candle_time = now - timedelta(minutes=(len(candles) - 1 - index) * 5)
        series.append(
            CandleState(
                symbol=symbol,
                timeframe=timeframe,
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle.get("volume", 100.0 + index)),
                candle_start=candle_time,
                is_closed=True,
                last_update=candle_time,
            )
        )

    current = series[-1]
    history = tuple(series[:-1])
    return MarketSnapshot(
        symbol=symbol,
        latest_price=current.close,
        candles={timeframe: current},
        volume_24h=1000.0,
        snapshot_time=current.candle_start,
        candle_history={timeframe: history},
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def detector_context(
    candles: list[dict[str, float]],
    *,
    symbol: str = "KRW-BTC",
    timeframe: str = "5m",
    config: dict[str, object] | None = None,
) -> DetectorContext:
    snapshot = snapshot_with_custom_candles(candles, symbol=symbol, timeframe=timeframe)
    return DetectorContext(
        snapshot=snapshot,
        symbol=symbol,
        timeframe=timeframe,
        config=config or {},
    )


def detector_context_from_snapshot(
    snapshot: MarketSnapshot,
    *,
    symbol: str | None = None,
    timeframe: str = "5m",
    config: dict[str, object] | None = None,
) -> DetectorContext:
    return DetectorContext(
        snapshot=snapshot,
        symbol=symbol or snapshot.symbol,
        timeframe=timeframe,
        config=config or {},
    )
