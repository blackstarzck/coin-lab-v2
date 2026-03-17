from __future__ import annotations

from .breakout_v1 import BreakoutV1Plugin
from .smc_confluence_v1 import SmcConfluenceV1Plugin

BUILTIN_STRATEGY_PLUGINS = (BreakoutV1Plugin(), SmcConfluenceV1Plugin())

__all__ = ["BUILTIN_STRATEGY_PLUGINS", "BreakoutV1Plugin", "SmcConfluenceV1Plugin"]
