from __future__ import annotations

from time import monotonic

import httpx

from ...infrastructure.repositories.lab_store import LabStore


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


class UniverseService:
    CATALOG_CACHE_TTL_SEC: int = 30
    TICKER_CHUNK_SIZE: int = 80
    FALLBACK_SYMBOLS: tuple[str, ...] = ("KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE")

    def __init__(self, store: LabStore, upbit_rest_base_url: str = "https://api.upbit.com") -> None:
        self.store = store
        self.upbit_rest_base_url = upbit_rest_base_url.rstrip("/")
        self._catalog_cache: dict[str, tuple[float, list[dict[str, object]]]] = {}

    def get_current(self) -> list[dict[str, object]]:
        rows = self.store.get_current_universe()
        return [
            {
                "symbol": str(item.get("symbol", "KRW-BTC")),
                "turnover_24h_krw": item.get("turnover_24h_krw", 152300000000),
                "surge_score": item.get("surge_score", 0.93),
                "selected": bool(item.get("selected", True)),
                "active_compare_session_count": 0,
                "has_open_position": False,
                "has_recent_signal": False,
                "risk_blocked": False,
            }
            for item in rows
        ]

    def catalog(self, quote: str = "KRW", query: str | None = None, limit: int = 10) -> list[dict[str, object]]:
        normalized_quote = (quote or "KRW").strip().upper()
        safe_limit = min(max(limit, 1), 100)
        catalog = self._get_catalog(normalized_quote)

        normalized_query = (query or "").strip().lower()
        if normalized_query:
            filtered = [item for item in catalog if self._matches_query(item, normalized_query)]
            filtered.sort(key=lambda item: self._search_rank(item, normalized_query))
            return filtered[:safe_limit]

        return catalog[:safe_limit]

    def preview(self, symbol_scope: dict[str, object]) -> dict[str, object]:
        raw_max_symbols = symbol_scope.get("max_symbols", 4)
        max_symbols = raw_max_symbols if isinstance(raw_max_symbols, int) else 4
        symbols = ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"][:max_symbols]
        return {"symbols": symbols, "count": len(symbols)}

    def _get_catalog(self, quote: str) -> list[dict[str, object]]:
        cached = self._catalog_cache.get(quote)
        if cached and monotonic() - cached[0] < self.CATALOG_CACHE_TTL_SEC:
            return [dict(item) for item in cached[1]]

        try:
            markets = self._fetch_market_rows(quote)
            if not markets:
                raise ValueError("empty market list")
            ticker_rows = self._fetch_ticker_rows([str(item.get("market")) for item in markets])
            catalog = [
                {
                    "symbol": symbol,
                    "korean_name": str(item.get("korean_name", symbol.replace(f"{quote}-", ""))),
                    "english_name": str(item.get("english_name", symbol.replace(f"{quote}-", ""))),
                    "market_warning": item.get("market_warning"),
                    "turnover_24h_krw": float(ticker_rows.get(symbol, {}).get("acc_trade_price_24h", 0) or 0),
                    "trade_price": self._optional_float(ticker_rows.get(symbol, {}).get("trade_price")),
                }
                for item in markets
                for symbol in [str(item.get("market", ""))]
                if symbol
            ]
            catalog.sort(key=lambda item: (-float(item["turnover_24h_krw"]), str(item["symbol"])))
        except Exception:
            catalog = self._fallback_catalog(quote)

        self._catalog_cache[quote] = (monotonic(), catalog)
        return [dict(item) for item in catalog]

    def _fetch_market_rows(self, quote: str) -> list[dict[str, object]]:
        response = httpx.get(
            f"{self.upbit_rest_base_url}/v1/market/all",
            params={"isDetails": "true"},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        prefix = f"{quote}-"
        return [
            item
            for item in payload
            if isinstance(item, dict) and str(item.get("market", "")).startswith(prefix)
        ]

    def _fetch_ticker_rows(self, symbols: list[str]) -> dict[str, dict[str, object]]:
        rows: dict[str, dict[str, object]] = {}
        for chunk in _chunked(symbols, self.TICKER_CHUNK_SIZE):
            if not chunk:
                continue
            response = httpx.get(
                f"{self.upbit_rest_base_url}/v1/ticker",
                params={"markets": ",".join(chunk)},
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                symbol = str(item.get("market", ""))
                if symbol:
                    rows[symbol] = item
        return rows

    def _fallback_catalog(self, quote: str) -> list[dict[str, object]]:
        prefix = f"{quote}-"
        current_rows = self.store.get_current_universe()
        ranked_symbols = [
            str(item.get("symbol", ""))
            for item in current_rows
            if str(item.get("symbol", "")).startswith(prefix)
        ]
        ranked_symbols.extend(symbol for symbol in self.FALLBACK_SYMBOLS if symbol.startswith(prefix))

        catalog: list[dict[str, object]] = []
        seen: set[str] = set()
        turnover_by_symbol = {
            str(item.get("symbol", "")): self._optional_float(item.get("turnover_24h_krw")) or 0.0
            for item in current_rows
        }
        for symbol in ranked_symbols:
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            catalog.append(
                {
                    "symbol": symbol,
                    "korean_name": symbol.replace(prefix, ""),
                    "english_name": symbol.replace(prefix, ""),
                    "market_warning": None,
                    "turnover_24h_krw": turnover_by_symbol.get(symbol, 0.0),
                    "trade_price": None,
                }
            )
        return catalog

    def _matches_query(self, item: dict[str, object], query: str) -> bool:
        candidates = (
            str(item.get("symbol", "")).lower(),
            str(item.get("korean_name", "")).lower(),
            str(item.get("english_name", "")).lower(),
        )
        return any(query in candidate for candidate in candidates)

    def _search_rank(self, item: dict[str, object], query: str) -> tuple[int, int, float, str]:
        symbol = str(item.get("symbol", "")).lower()
        korean_name = str(item.get("korean_name", "")).lower()
        english_name = str(item.get("english_name", "")).lower()
        if symbol == query or korean_name == query or english_name == query:
            score = 0
        elif symbol.startswith(query):
            score = 1
        elif korean_name.startswith(query) or english_name.startswith(query):
            score = 2
        else:
            score = 3
        return (score, 0 if symbol == "krw-btc" else 1, -float(item.get("turnover_24h_krw", 0) or 0), symbol)

    def _optional_float(self, value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None
