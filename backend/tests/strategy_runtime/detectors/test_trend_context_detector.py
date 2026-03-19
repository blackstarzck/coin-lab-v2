from __future__ import annotations

from app.application.strategy_runtime.detectors import TrendContextDetector

from .fixtures import detector_context


def test_trend_context_detector_returns_not_ready_when_history_is_short() -> None:
    detector = TrendContextDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5},
            {"open": 100.5, "high": 101.5, "low": 100.0, "close": 101.0},
            {"open": 101.0, "high": 102.0, "low": 100.5, "close": 101.6},
        ],
        config={"lookback": 4, "direction": "bullish"},
    )

    result = detector.evaluate(context)

    assert result.ready is False
    assert result.matched is False
    assert result.reason_codes == ("DETECTOR_HISTORY_NOT_READY",)


def test_trend_context_detector_matches_bullish_trend_and_keeps_primary_context() -> None:
    detector = TrendContextDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.0},
            {"open": 102.0, "high": 104.5, "low": 101.5, "close": 104.0},
            {"open": 104.0, "high": 106.5, "low": 103.5, "close": 106.0},
            {"open": 106.0, "high": 108.0, "low": 105.5, "close": 107.0},
            {"open": 108.0, "high": 108.4, "low": 106.2, "close": 106.8},
            {"open": 106.9, "high": 112.0, "low": 106.6, "close": 111.2},
            {"open": 111.0, "high": 113.0, "low": 109.4, "close": 112.6},
            {"open": 112.4, "high": 113.2, "low": 111.8, "close": 112.9},
            {"open": 107.4, "high": 111.4, "low": 106.9, "close": 110.9},
        ],
        config={"lookback": 8, "direction": "bullish"},
    )

    result = detector.evaluate(context)

    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.trend_state == "trend_up"
    assert result.primary.support == 106.6
    assert result.primary.average_close == 108.925
