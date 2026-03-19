from __future__ import annotations

from app.application.strategy_runtime.detectors import OrderBlockDetector

from .fixtures import detector_context


def test_order_block_detector_matches_bullish_retest_zone() -> None:
    detector = OrderBlockDetector()
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
        config={
            "direction": "bullish",
            "lookback": 6,
            "body_ratio_threshold": 0.5,
            "body_pct_threshold": 0.01,
            "retest_tolerance_pct": 0.002,
            "invalidation_buffer_pct": 0.002,
        },
    )

    result = detector.evaluate(context)

    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.lower == 106.2
    assert result.primary.upper == 108.0
    assert result.primary.retested is True


def test_order_block_detector_returns_not_ready_when_lookback_window_is_missing() -> None:
    detector = OrderBlockDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.5, "low": 99.5, "close": 101.2},
            {"open": 101.2, "high": 102.0, "low": 100.8, "close": 101.8},
            {"open": 101.8, "high": 102.3, "low": 101.0, "close": 101.4},
            {"open": 101.4, "high": 101.6, "low": 100.5, "close": 100.8},
            {"open": 100.8, "high": 103.5, "low": 100.6, "close": 103.2},
            {"open": 103.2, "high": 104.0, "low": 102.7, "close": 103.5},
        ],
        config={
            "direction": "bullish",
            "lookback": 6,
            "body_ratio_threshold": 0.5,
            "body_pct_threshold": 0.01,
            "retest_tolerance_pct": 0.002,
            "invalidation_buffer_pct": 0.002,
        },
    )

    result = detector.evaluate(context)

    assert result.ready is False
    assert result.matched is False
    assert result.reason_codes == ("DETECTOR_HISTORY_NOT_READY",)
