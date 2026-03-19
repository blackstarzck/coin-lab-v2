from __future__ import annotations

from app.application.services.fill_engine import FillEngine
from app.domain.entities.session import ExitReason, Position


class ExitExecutionPolicy:
    def __init__(self, fill_engine: FillEngine) -> None:
        self.fill_engine = fill_engine

    def evaluate(
        self,
        *,
        position: Position,
        current_price: float,
        candle_high: float,
        candle_low: float,
        exit_config: dict[str, object],
        bar_count: int,
    ) -> ExitReason | None:
        return self.fill_engine.evaluate_exit_triggers(
            position=position,
            current_price=current_price,
            candle_high=candle_high,
            candle_low=candle_low,
            exit_config=exit_config,
            bar_count=bar_count,
        )
