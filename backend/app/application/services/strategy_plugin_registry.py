from __future__ import annotations

from collections.abc import Iterable

from app.domain.interfaces import StrategyPlugin
from app.plugins import BUILTIN_STRATEGY_PLUGINS


class StrategyPluginRegistry:
    def __init__(self, plugins: Iterable[StrategyPlugin] | None = None) -> None:
        self._plugins: dict[str, StrategyPlugin] = {}
        for plugin in plugins or BUILTIN_STRATEGY_PLUGINS:
            self.register(plugin)

    def register(self, plugin: StrategyPlugin) -> None:
        self._plugins[plugin.plugin_id] = plugin

    def get(self, plugin_id: str | None) -> StrategyPlugin | None:
        if not plugin_id:
            return None
        return self._plugins.get(plugin_id)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins.keys()))
