from __future__ import annotations

from app.application.strategy_runtime.detectors import StructureBreakDetector

from .fixtures import detector_context


def test_structure_break_detector_returns_not_ready_when_history_is_short() -> None:
    detector = StructureBreakDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.6},
            {"open": 100.6, "high": 101.5, "low": 100.2, "close": 101.2},
            {"open": 101.2, "high": 101.7, "low": 100.8, "close": 101.0},
            {"open": 101.0, "high": 102.0, "low": 100.9, "close": 101.8},
            {"open": 101.8, "high": 102.1, "low": 101.1, "close": 101.5},
        ],
        config={"swing_lookback": 3, "break_confirmation": "close"},
    )

    result = detector.evaluate(context)

    assert result.ready is False
    assert result.matched is False
    assert result.reason_codes == ("DETECTOR_HISTORY_NOT_READY",)


def test_structure_break_detector_matches_bullish_bos() -> None:
    detector = StructureBreakDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.4},
            {"open": 100.4, "high": 101.5, "low": 100.1, "close": 101.1},
            {"open": 101.1, "high": 102.3, "low": 100.9, "close": 102.0},
            {"open": 102.0, "high": 102.4, "low": 101.1, "close": 101.8},
            {"open": 101.8, "high": 103.0, "low": 101.5, "close": 102.7},
            {"open": 102.7, "high": 103.2, "low": 102.2, "close": 102.9},
            {"open": 102.9, "high": 104.6, "low": 102.8, "close": 104.2},
        ],
        config={"swing_lookback": 3, "break_confirmation": "close", "break_buffer_pct": 0.0},
    )

    result = detector.evaluate(context)

    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.direction == "bullish"
    assert result.primary.break_type == "bos"
    assert result.primary.reference_price == 102.9
    assert result.primary.break_price == 104.2


def test_structure_break_detector_matches_bearish_choch_when_uptrend_breaks_down() -> None:
    detector = StructureBreakDetector()
    context = detector_context(
        [
            {"open": 100.0, "high": 101.0, "low": 99.7, "close": 100.5},
            {"open": 100.5, "high": 102.0, "low": 100.3, "close": 101.6},
            {"open": 101.6, "high": 103.0, "low": 101.4, "close": 102.5},
            {"open": 102.5, "high": 102.8, "low": 101.9, "close": 102.2},
            {"open": 102.2, "high": 102.6, "low": 101.2, "close": 101.5},
            {"open": 101.5, "high": 101.9, "low": 100.8, "close": 101.0},
            {"open": 101.0, "high": 101.2, "low": 98.9, "close": 99.2},
        ],
        config={"swing_lookback": 3, "break_confirmation": "close", "break_buffer_pct": 0.0},
    )

    result = detector.evaluate(context)

    assert result.ready is True
    assert result.matched is True
    assert result.primary is not None
    assert result.primary.direction == "bearish"
    assert result.primary.break_type == "choch"
    assert result.primary.reference_price == 101.0
    assert result.primary.break_price == 99.2
