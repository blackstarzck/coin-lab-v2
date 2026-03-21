from __future__ import annotations

from app.domain.interfaces import StrategyPluginFieldDefinition, StrategyPluginFieldOption

TIMEFRAME_OPTIONS: tuple[StrategyPluginFieldOption, ...] = (
    StrategyPluginFieldOption(label="1m", value="1m"),
    StrategyPluginFieldOption(label="5m", value="5m"),
    StrategyPluginFieldOption(label="15m", value="15m"),
    StrategyPluginFieldOption(label="1h", value="1h"),
)


def timeframe_field(helper_text: str, *, summary: bool = True) -> StrategyPluginFieldDefinition:
    return StrategyPluginFieldDefinition(
        key="timeframe",
        label="기준 타임프레임",
        kind="select",
        helper_text=helper_text,
        options=TIMEFRAME_OPTIONS,
        summary=summary,
    )
