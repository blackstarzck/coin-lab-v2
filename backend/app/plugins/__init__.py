from __future__ import annotations

from .breakout_v1 import BreakoutV1Plugin
from .ob_fvg_bull_reclaim_v1 import ObFvgBullReclaimV1Plugin
from .smc_confluence_v1 import SmcConfluenceV1Plugin

BUILTIN_STRATEGY_PLUGINS = (BreakoutV1Plugin(), SmcConfluenceV1Plugin(), ObFvgBullReclaimV1Plugin())

__all__ = [
    "BUILTIN_STRATEGY_PLUGINS",
    "BreakoutV1Plugin",
    "ObFvgBullReclaimV1Plugin",
    "SmcConfluenceV1Plugin",
]
