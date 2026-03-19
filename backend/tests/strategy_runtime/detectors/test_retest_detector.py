from __future__ import annotations

from app.application.strategy_runtime.detectors import OrderBlockDetector, RetestDetector, StructureBreakDetector

from .fixtures import detector_context_from_snapshot, snapshot_with_custom_candles


def test_retest_detector_accepts_order_block_retest_with_confirmation() -> None:
    order_block_detector = OrderBlockDetector()
    retest_detector = RetestDetector()
    snapshot = snapshot_with_custom_candles(
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
        ]
    )
    zone_result = order_block_detector.evaluate(
        detector_context_from_snapshot(
            snapshot,
            config={
                "direction": "bullish",
                "lookback": 6,
                "body_ratio_threshold": 0.5,
                "body_pct_threshold": 0.01,
                "retest_tolerance_pct": 0.002,
                "invalidation_buffer_pct": 0.002,
            },
        )
    )

    result = retest_detector.evaluate(
        detector_context_from_snapshot(
            snapshot,
            config={
                "target": zone_result.primary,
                "zone_kind": "order_block",
                "tolerance_pct": 0.002,
                "require_rejection_candle": True,
            },
        )
    )

    assert zone_result.primary is not None
    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.zone_kind == "order_block"
    assert result.primary.accepted is True
    assert result.primary.rejection_confirmed is True


def test_retest_detector_rejects_when_rejection_candle_is_missing() -> None:
    order_block_detector = OrderBlockDetector()
    retest_detector = RetestDetector()
    snapshot = snapshot_with_custom_candles(
        [
            {"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.0},
            {"open": 102.0, "high": 104.5, "low": 101.5, "close": 104.0},
            {"open": 104.0, "high": 106.5, "low": 103.5, "close": 106.0},
            {"open": 106.0, "high": 108.0, "low": 105.5, "close": 107.0},
            {"open": 108.0, "high": 108.4, "low": 106.2, "close": 106.8},
            {"open": 106.9, "high": 112.0, "low": 106.6, "close": 111.2},
            {"open": 111.0, "high": 113.0, "low": 109.4, "close": 112.6},
            {"open": 112.4, "high": 113.2, "low": 111.8, "close": 112.9},
            {"open": 108.8, "high": 109.0, "low": 106.9, "close": 107.2},
        ]
    )
    zone_result = order_block_detector.evaluate(
        detector_context_from_snapshot(
            snapshot,
            config={
                "direction": "bullish",
                "lookback": 6,
                "body_ratio_threshold": 0.5,
                "body_pct_threshold": 0.01,
                "retest_tolerance_pct": 0.002,
                "invalidation_buffer_pct": 0.002,
            },
        )
    )

    result = retest_detector.evaluate(
        detector_context_from_snapshot(
            snapshot,
            config={
                "target": zone_result.primary,
                "zone_kind": "order_block",
                "tolerance_pct": 0.002,
                "require_rejection_candle": True,
            },
        )
    )

    assert zone_result.primary is not None
    assert result.ready is True
    assert result.matched is False
    assert result.primary is not None
    assert result.primary.accepted is False
    assert result.primary.rejection_confirmed is False


def test_retest_detector_accepts_bullish_structure_break_level_retest() -> None:
    structure_break_detector = StructureBreakDetector()
    retest_detector = RetestDetector()
    break_snapshot = snapshot_with_custom_candles(
        [
            {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.4},
            {"open": 100.4, "high": 101.5, "low": 100.1, "close": 101.1},
            {"open": 101.1, "high": 102.3, "low": 100.9, "close": 102.0},
            {"open": 102.0, "high": 102.4, "low": 101.1, "close": 101.8},
            {"open": 101.8, "high": 103.0, "low": 101.5, "close": 102.7},
            {"open": 102.7, "high": 103.2, "low": 102.2, "close": 102.9},
            {"open": 102.9, "high": 104.6, "low": 102.8, "close": 104.2},
        ]
    )
    structure_break_result = structure_break_detector.evaluate(
        detector_context_from_snapshot(
            break_snapshot,
            config={"swing_lookback": 3, "break_confirmation": "close", "break_buffer_pct": 0.0},
        )
    )

    retest_snapshot = snapshot_with_custom_candles(
        [
            {"open": 100.4, "high": 101.5, "low": 100.1, "close": 101.1},
            {"open": 101.1, "high": 102.3, "low": 100.9, "close": 102.0},
            {"open": 102.0, "high": 102.4, "low": 101.1, "close": 101.8},
            {"open": 101.8, "high": 103.0, "low": 101.5, "close": 102.7},
            {"open": 102.7, "high": 103.2, "low": 102.2, "close": 102.9},
            {"open": 102.9, "high": 104.6, "low": 102.8, "close": 104.2},
            {"open": 103.0, "high": 104.8, "low": 102.8, "close": 104.6},
        ]
    )
    result = retest_detector.evaluate(
        detector_context_from_snapshot(
            retest_snapshot,
            config={
                "target": structure_break_result.primary,
                "zone_kind": "structure_break",
                "tolerance_pct": 0.001,
                "require_rejection_candle": True,
            },
        )
    )

    assert structure_break_result.primary is not None
    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.zone_kind == "structure_break"
    assert result.primary.accepted is True
