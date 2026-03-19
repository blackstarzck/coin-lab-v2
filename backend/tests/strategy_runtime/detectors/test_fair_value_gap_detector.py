from __future__ import annotations

from app.application.strategy_runtime.detectors import FairValueGapDetector

from .fixtures import detector_context


def test_fair_value_gap_detector_matches_bullish_retest_zone() -> None:
    detector = FairValueGapDetector()
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
            "gap_threshold_pct": 0.005,
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
    assert result.primary.lower == 108.4
    assert result.primary.upper == 109.4
    assert result.primary.retested is True


def test_fair_value_gap_detector_returns_no_match_when_gap_is_invalidated() -> None:
    detector = FairValueGapDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5},
            {"open": 100.5, "high": 106.0, "low": 100.4, "close": 105.8},
            {"open": 106.2, "high": 107.0, "low": 106.1, "close": 106.8},
            {"open": 106.5, "high": 106.9, "low": 100.0, "close": 100.2},
            {"open": 100.3, "high": 101.0, "low": 99.8, "close": 100.7},
        ],
        config={
            "direction": "bullish",
            "gap_threshold_pct": 0.001,
            "body_ratio_threshold": 0.5,
            "body_pct_threshold": 0.01,
            "retest_tolerance_pct": 0.001,
            "invalidation_buffer_pct": 0.002,
        },
    )

    result = detector.evaluate(context)

    assert result.ready is True
    assert result.matched is False
    assert result.reason_codes == ("DETECTOR_NO_MATCH",)
