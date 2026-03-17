from __future__ import annotations

from .breakout_v1 import BreakoutV1Plugin

BUILTIN_STRATEGY_PLUGINS = (BreakoutV1Plugin(),)

__all__ = ["BUILTIN_STRATEGY_PLUGINS", "BreakoutV1Plugin"]
