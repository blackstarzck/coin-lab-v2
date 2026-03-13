from __future__ import annotations

from collections.abc import Iterable

DEFAULT_SYMBOLS: tuple[str, ...] = ("KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP")


def normalize_symbols(raw_symbols: object) -> list[str]:
    if not isinstance(raw_symbols, list):
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw_symbols:
        symbol = str(item).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        normalized.append(symbol)
    return normalized


def strategy_universe(config_json: dict[str, object]) -> dict[str, object]:
    raw_universe = config_json.get("universe")
    if isinstance(raw_universe, dict):
        return raw_universe
    return {}


def strategy_universe_mode(config_json: dict[str, object]) -> str | None:
    mode = strategy_universe(config_json).get("mode")
    return str(mode) if isinstance(mode, str) else None


def strategy_static_symbols(config_json: dict[str, object]) -> list[str]:
    if strategy_universe_mode(config_json) != "static":
        return []
    return normalize_symbols(strategy_universe(config_json).get("symbols"))


def strategy_dynamic_max_symbols(config_json: dict[str, object]) -> int | None:
    universe = strategy_universe(config_json)
    if str(universe.get("mode")) != "dynamic":
        return None
    raw_max_symbols = universe.get("max_symbols")
    if isinstance(raw_max_symbols, int) and raw_max_symbols > 0:
        return raw_max_symbols
    return None


def resolve_strategy_symbols(
    requested_symbols: object,
    strategy_config: dict[str, object],
    current_universe_symbols: Iterable[str],
) -> list[str]:
    requested = normalize_symbols(requested_symbols)
    if requested:
        return requested

    configured_static = strategy_static_symbols(strategy_config)
    if configured_static:
        return configured_static

    fallback_symbols = normalize_symbols(list(current_universe_symbols))
    if not fallback_symbols:
        fallback_symbols = list(DEFAULT_SYMBOLS)

    dynamic_max_symbols = strategy_dynamic_max_symbols(strategy_config)
    if dynamic_max_symbols is not None:
        return fallback_symbols[:dynamic_max_symbols]
    return fallback_symbols
