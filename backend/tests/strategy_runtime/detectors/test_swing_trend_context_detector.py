from __future__ import annotations

from app.application.strategy_runtime.detectors import SwingTrendContextDetector
from tests.strategy_runtime.detectors.fixtures import detector_context


def test_swing_trend_context_detector_matches_higher_high_higher_low_bull_mode() -> None:
    detector = SwingTrendContextDetector()
    result = detector.evaluate(
        detector_context(
            [
                {"open": 102.0, "high": 110.0, "low": 100.0, "close": 105.0},
                {"open": 108.0, "high": 120.0, "low": 106.0, "close": 118.0},
                {"open": 114.0, "high": 115.0, "low": 104.0, "close": 110.0},
                {"open": 120.0, "high": 130.0, "low": 112.0, "close": 128.0},
                {"open": 122.0, "high": 125.0, "low": 110.0, "close": 121.0},
                {"open": 126.0, "high": 136.0, "low": 118.0, "close": 134.0},
            ],
            timeframe="1h",
            config={"direction": "bullish", "width": 1},
        )
    )

    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.trend_state == "trend_up"
    assert result.primary.support == 110.0
    assert result.primary.resistance == 130.0
