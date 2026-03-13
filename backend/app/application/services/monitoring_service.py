from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from ...domain.entities.session import PositionState, Session
from ...infrastructure.repositories.lab_store import LabStore
from .strategy_performance import StrategyPerformanceSnapshot, build_strategy_performance_map


class MonitoringService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def get_summary(self) -> dict[str, object]:
        sessions = self.store.list_sessions()
        strategies = self.store.list_strategies()
        universe_rows = [dict(item) for item in self.store.get_current_universe()]
        running = [item for item in sessions if item.status.value == "RUNNING"]
        paper = [item for item in running if item.mode.value == "PAPER"]
        live = [item for item in running if item.mode.value == "LIVE"]
        failed = [item for item in sessions if item.status.value == "FAILED"]
        degraded = [item for item in running if self._is_degraded(item)]

        session_ids = [session.id for session in sessions]
        all_signals = self.store.list_signals_for_sessions(session_ids)
        all_positions = self.store.list_positions_for_sessions(session_ids)
        all_risk_events = self.store.list_risk_events_for_sessions(session_ids)

        signals_by_session = self._group_by_session_id(all_signals)
        positions_by_session = self._group_by_session_id(all_positions)
        risk_events_by_session = self._group_by_session_id(all_risk_events)

        version_ids = list(
            dict.fromkeys(
                [
                    session.strategy_version_id
                    for session in sessions
                    if session.strategy_version_id
                ]
                + [
                    str(strategy.latest_version_id)
                    for strategy in strategies
                    if strategy.latest_version_id
                ]
            )
        )
        version_cache = {
            version.id: version
            for version in self.store.list_strategy_versions_by_ids(version_ids)
        }
        performance_by_strategy = build_strategy_performance_map(sessions, list(version_cache.values()))

        active_symbols_by_session = {session.id: self._active_symbols(session) for session in running}
        active_symbols = sorted({symbol for symbols in active_symbols_by_session.values() for symbol in symbols})
        recent_signals = sorted(all_signals, key=lambda item: item.snapshot_time, reverse=True)[:20]
        recent_signal_symbols = {signal.symbol for signal in recent_signals}
        blocked_signals_last_hour = [
            signal
            for signal in all_signals
            if signal.blocked and signal.snapshot_time >= datetime.now(UTC) - timedelta(hours=1)
        ]
        open_position_symbols = {
            position.symbol
            for rows in positions_by_session.values()
            for position in rows
            if position.position_state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}
        }
        risk_blocked_symbols = {event.symbol for event in all_risk_events if event.symbol}

        return {
            "status_bar": {
                "running_session_count": len(running),
                "paper_session_count": len(paper),
                "live_session_count": len(live),
                "failed_session_count": len(failed),
                "degraded_session_count": len(degraded),
                "active_symbol_count": len(active_symbols),
            },
            "strategy_cards": self._strategy_cards(
                strategies,
                running,
                version_cache,
                signals_by_session,
                performance_by_strategy,
            ),
            "universe_summary": {
                "active_symbol_count": len(active_symbols),
                "watchlist_symbol_count": sum(1 for item in universe_rows if not bool(item.get("selected", True))),
                "with_open_position_count": len(open_position_symbols),
                "with_recent_signal_count": len(recent_signal_symbols),
                "symbols": [
                    {
                        "symbol": str(item.get("symbol", "")),
                        "turnover_24h_krw": item.get("turnover_24h_krw"),
                        "surge_score": item.get("surge_score"),
                        "selected": bool(item.get("selected", True)),
                        "active_compare_session_count": sum(
                            1 for symbols in active_symbols_by_session.values() if str(item.get("symbol", "")) in symbols
                        ),
                        "has_open_position": str(item.get("symbol", "")) in open_position_symbols,
                        "has_recent_signal": str(item.get("symbol", "")) in recent_signal_symbols,
                        "risk_blocked": str(item.get("symbol", "")) in risk_blocked_symbols,
                    }
                    for item in universe_rows
                ],
            },
            "risk_overview": {
                "active_alert_count": len(all_risk_events),
                "blocked_signal_count_1h": len(blocked_signals_last_hour),
                "daily_loss_limit_session_count": len(
                    {event.session_id for event in all_risk_events if event.code == "RISK_DAILY_LOSS_LIMIT_REACHED"}
                ),
                "max_drawdown_session_count": len(
                    {event.session_id for event in all_risk_events if event.code == "RISK_MAX_DRAWDOWN_REACHED"}
                ),
                "items": [
                    {
                        "id": event.id,
                        "session_id": event.session_id,
                        "severity": event.severity,
                        "code": event.code,
                        "message": event.message,
                        "created_at": event.created_at,
                    }
                    for event in sorted(all_risk_events, key=lambda item: item.created_at, reverse=True)[:20]
                ],
            },
            "recent_signals": recent_signals,
        }

    def _group_by_session_id(self, items: list[object]) -> dict[str, list[object]]:
        grouped: dict[str, list[object]] = defaultdict(list)
        for item in items:
            session_id = getattr(item, "session_id", None)
            if isinstance(session_id, str):
                grouped[session_id].append(item)
        return grouped

    def _active_symbols(self, session: Session) -> list[str]:
        active_symbols = session.symbol_scope_json.get("active_symbols")
        if isinstance(active_symbols, list):
            return [str(symbol) for symbol in active_symbols]
        symbols = session.symbol_scope_json.get("symbols")
        if isinstance(symbols, list):
            return [str(symbol) for symbol in symbols]
        return []

    def _is_degraded(self, session: Session) -> bool:
        connection_state = str(session.health_json.get("connection_state", "CONNECTED")).upper()
        snapshot_consistency = str(session.health_json.get("snapshot_consistency", "HEALTHY")).upper()
        return connection_state in {"DEGRADED", "DISCONNECTED", "RECONNECTING"} or snapshot_consistency != "HEALTHY"

    def _strategy_cards(
        self,
        strategies: list[object],
        running_sessions: list[Session],
        version_cache: dict[str, object],
        signals_by_session: dict[str, list[object]],
        performance_by_strategy: dict[str, StrategyPerformanceSnapshot],
    ) -> list[dict[str, object]]:
        cards: list[dict[str, object]] = []
        for strategy in strategies:
            strategy_sessions = [
                session
                for session in running_sessions
                if (
                    version_cache.get(session.strategy_version_id) is not None
                    and getattr(version_cache[session.strategy_version_id], "strategy_id", None) == strategy.id
                )
            ]
            strategy_signals = [
                signal
                for session in strategy_sessions
                for signal in signals_by_session.get(session.id, [])
            ]
            latest_version = version_cache.get(strategy.latest_version_id) if strategy.latest_version_id else None
            performance = performance_by_strategy.get(strategy.id)
            cards.append(
                {
                    "strategy_id": strategy.id,
                    "strategy_key": strategy.strategy_key,
                    "strategy_name": strategy.name,
                    "strategy_type": strategy.strategy_type.value,
                    "latest_version_id": strategy.latest_version_id,
                    "latest_version_no": strategy.latest_version_no,
                    "is_active": strategy.is_active,
                    "is_validated": bool(getattr(latest_version, "is_validated", False)),
                    "active_session_count": len(strategy_sessions),
                    "last_7d_return_pct": performance.last_7d_return_pct if performance is not None else None,
                    "last_signal_at": max((signal.snapshot_time for signal in strategy_signals), default=None),
                }
            )
        return cards
