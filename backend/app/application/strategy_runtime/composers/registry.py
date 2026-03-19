from __future__ import annotations

from collections.abc import Iterable

from .base import StrategyComposer
from .breakout import BreakoutComposer
from .smc_confluence import SmcConfluenceComposer


class StrategyComposerRegistry:
    def __init__(self, composers: Iterable[StrategyComposer] | None = None) -> None:
        self._composers: dict[str, StrategyComposer] = {}
        for composer in composers or (BreakoutComposer(), SmcConfluenceComposer()):
            self.register(composer)

    def register(self, composer: StrategyComposer) -> None:
        self._composers[composer.composer_id] = composer

    def get(self, composer_id: str | None) -> StrategyComposer | None:
        if composer_id is None:
            return None
        return self._composers.get(composer_id)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._composers.keys()))
