from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from ...domain.entities.session import Order, OrderState, Position, PositionState, Session
from ...domain.entities.strategy import Strategy
from ...infrastructure.repositories.lab_store import LabStore
from .strategy_performance import StrategyPerformanceSnapshot, build_strategy_performance_map


class MonitoringService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def get_summary(self) -> dict[str, object]:
        sessions = self.store.list_sessions()
        strategies = self.store.list_strategies()
        strategy_by_id = {strategy.id: strategy for strategy in strategies}
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
        all_orders = [
            order
            for session_id in session_ids
            for order in self.store.list_session_orders(session_id)
        ]

        signals_by_session = self._group_by_session_id(all_signals)
        positions_by_session = self._group_by_session_id(all_positions)
        risk_events_by_session = self._group_by_session_id(all_risk_events)
        orders_by_session = self._group_by_session_id(all_orders)

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
        strategy_metrics = self._build_strategy_metrics(
            strategies,
            sessions,
            running,
            version_cache,
            signals_by_session,
            positions_by_session,
            risk_events_by_session,
            performance_by_strategy,
        )
        derived_trades = self._derive_trade_rows(all_orders, version_cache, strategy_by_id)

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
        latest_event_at = max(
            [
                *(signal.snapshot_time for signal in all_signals),
                *(event.created_at for event in all_risk_events),
                *(order.filled_at for order in all_orders if order.filled_at is not None),
            ],
            default=None,
        )

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
            "dashboard": {
                "hero": {
                    "title": "Strategy Arena",
                    "subtitle": "Coin Lab 실험실의 전략 성과와 실행 흐름을 한 화면에서 추적합니다.",
                    "active_strategy_count": len([item for item in strategy_metrics.values() if item["active_session_count"] > 0]),
                    "running_session_count": len(running),
                    "active_symbol_count": len(active_symbols),
                    "recent_trade_count": len(
                        [order for order in all_orders if order.order_state == OrderState.FILLED and order.filled_at is not None]
                    ),
                    "latest_event_at": latest_event_at,
                    "headline_strategy_name": self._best_strategy_name(strategy_metrics),
                },
                "strategy_strip": self._strategy_strip(strategy_metrics),
                "market_strip": self._market_strip(universe_rows, active_symbols, risk_blocked_symbols),
                "performance_history": self._performance_history(derived_trades, strategy_metrics),
                "live_activity": self._live_activity(all_signals, all_orders, all_risk_events, version_cache, strategy_by_id),
                "recent_trades": self._recent_trades(all_orders, version_cache, strategy_by_id),
                "leaderboard": self._leaderboard(strategy_metrics),
                "strategy_details": self._strategy_details(strategy_metrics),
                "market_details": self._market_details(
                    universe_rows,
                    active_symbols_by_session,
                    open_position_symbols,
                    recent_signal_symbols,
                    risk_blocked_symbols,
                ),
            },
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

    def _build_strategy_metrics(
        self,
        strategies: list[Strategy],
        sessions: list[Session],
        running_sessions: list[Session],
        version_cache: dict[str, object],
        signals_by_session: dict[str, list[object]],
        positions_by_session: dict[str, list[object]],
        risk_events_by_session: dict[str, list[object]],
        performance_by_strategy: dict[str, StrategyPerformanceSnapshot],
    ) -> dict[str, dict[str, object]]:
        metrics: dict[str, dict[str, object]] = {
            strategy.id: {
                "strategy_id": strategy.id,
                "strategy_name": strategy.name,
                "strategy_key": strategy.strategy_key,
                "strategy_type": strategy.strategy_type.value,
                "description": strategy.description,
                "labels": list(strategy.labels),
                "active_session_count": 0,
                "paper_session_count": 0,
                "live_session_count": 0,
                "account_value": 0.0,
                "initial_capital": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "return_pct": 0.0,
                "win_rate_pct": None,
                "trades": 0,
                "risk_alert_count": 0,
                "active_position_count": 0,
                "degraded_session_count": 0,
                "monitoring_state": "idle",
                "tracked_symbols": set(),
                "last_signal_at": None,
                "open_positions": [],
            }
            for strategy in strategies
        }

        running_ids = {session.id for session in running_sessions}
        for session in sessions:
            version = version_cache.get(session.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            if not isinstance(strategy_id, str) or strategy_id not in metrics:
                continue
            row = metrics[strategy_id]
            initial_capital = _as_float(session.performance_json.get("initial_capital"))
            realized_pnl = _as_float(session.performance_json.get("realized_pnl"))
            unrealized_pnl = _as_float(session.performance_json.get("unrealized_pnl"))
            trade_count = _as_int(session.performance_json.get("trade_count"))

            row["initial_capital"] = float(row["initial_capital"]) + initial_capital
            row["realized_pnl"] = float(row["realized_pnl"]) + realized_pnl
            row["unrealized_pnl"] = float(row["unrealized_pnl"]) + unrealized_pnl
            row["total_pnl"] = float(row["total_pnl"]) + realized_pnl + unrealized_pnl
            row["account_value"] = float(row["account_value"]) + initial_capital + realized_pnl + unrealized_pnl
            row["trades"] = int(row["trades"]) + trade_count
            tracked_symbols = row["tracked_symbols"]
            if isinstance(tracked_symbols, set):
                tracked_symbols.update(self._active_symbols(session))
            if session.id in running_ids:
                row["active_session_count"] = int(row["active_session_count"]) + 1
                if session.mode.value == "PAPER":
                    row["paper_session_count"] = int(row["paper_session_count"]) + 1
                if session.mode.value == "LIVE":
                    row["live_session_count"] = int(row["live_session_count"]) + 1
                if self._is_degraded(session):
                    row["degraded_session_count"] = int(row["degraded_session_count"]) + 1

            session_signals = signals_by_session.get(session.id, [])
            last_signal_at = max((signal.snapshot_time for signal in session_signals), default=None)
            if last_signal_at and (row["last_signal_at"] is None or last_signal_at > row["last_signal_at"]):
                row["last_signal_at"] = last_signal_at

            open_positions = [
                position
                for position in positions_by_session.get(session.id, [])
                if position.position_state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}
            ]
            row["active_position_count"] = int(row["active_position_count"]) + len(open_positions)
            row_positions = row["open_positions"]
            if isinstance(row_positions, list):
                row_positions.extend(open_positions)

            row["risk_alert_count"] = int(row["risk_alert_count"]) + len(risk_events_by_session.get(session.id, []))

        for strategy_id, row in metrics.items():
            performance = performance_by_strategy.get(strategy_id)
            initial_capital = float(row["initial_capital"])
            total_pnl = float(row["total_pnl"])
            row["return_pct"] = (
                performance.last_7d_return_pct
                if performance is not None and performance.last_7d_return_pct is not None
                else ((total_pnl / initial_capital) * 100 if initial_capital > 0 else 0.0)
            )
            row["win_rate_pct"] = performance.last_7d_win_rate if performance is not None else None
            tracked_symbols = row["tracked_symbols"]
            if isinstance(tracked_symbols, set):
                row["tracked_symbols"] = sorted(tracked_symbols)
            active_session_count = int(row["active_session_count"])
            degraded_session_count = int(row["degraded_session_count"])
            row["monitoring_state"] = (
                "idle"
                if active_session_count == 0
                else "degraded"
                if degraded_session_count > 0
                else "running"
            )
            open_positions = row["open_positions"]
            if isinstance(open_positions, list):
                row["open_positions"] = sorted(
                    [
                        {
                            "symbol": position.symbol,
                            "side": position.side,
                            "quantity": position.quantity,
                            "avg_entry_price": position.avg_entry_price,
                            "unrealized_pnl_pct": position.unrealized_pnl_pct,
                        }
                        for position in open_positions
                    ],
                    key=lambda item: abs(_as_float(item["unrealized_pnl_pct"])),
                    reverse=True,
                )[:3]

        return metrics

    def _derive_trade_rows(
        self,
        orders: list[Order],
        version_cache: dict[str, object],
        strategy_by_id: dict[str, Strategy],
    ) -> list[dict[str, object]]:
        open_entries: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        trade_rows: list[dict[str, object]] = []

        filled_orders = sorted(
            [
                order
                for order in orders
                if order.order_state == OrderState.FILLED
                and order.filled_at is not None
                and order.executed_price is not None
                and order.executed_qty > 0
            ],
            key=lambda item: item.filled_at or datetime.min.replace(tzinfo=UTC),
        )

        for order in filled_orders:
            version = version_cache.get(order.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            if not isinstance(strategy_id, str):
                continue
            strategy = strategy_by_id.get(strategy_id)
            key = (order.session_id, order.symbol)
            role = str(order.order_role)
            if role == "ENTRY":
                open_entries[key].append(
                    {
                        "remaining_qty": order.executed_qty,
                        "entry_price": float(order.executed_price),
                        "entry_time": order.filled_at,
                        "strategy_id": strategy_id,
                        "strategy_name": strategy.name if strategy is not None else strategy_id,
                    }
                )
                continue

            if role not in {"EXIT", "STOP_LOSS", "TAKE_PROFIT"}:
                continue

            remaining_exit_qty = order.executed_qty
            while remaining_exit_qty > 0 and open_entries[key]:
                entry = open_entries[key][0]
                matched_qty = min(remaining_exit_qty, _as_float(entry["remaining_qty"]))
                entry_price = _as_float(entry["entry_price"])
                exit_price = float(order.executed_price)
                cost_basis = entry_price * matched_qty
                pnl = (exit_price - entry_price) * matched_qty
                trade_rows.append(
                    {
                        "id": f"trade_{order.id}_{len(trade_rows)}",
                        "strategy_id": strategy_id,
                        "strategy_name": str(entry["strategy_name"]),
                        "symbol": order.symbol,
                        "entry_time": entry["entry_time"],
                        "exit_time": order.filled_at,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "qty": matched_qty,
                        "pnl": pnl,
                        "pnl_pct": ((pnl / cost_basis) * 100) if cost_basis > 0 else 0.0,
                        "exit_reason": role,
                    }
                )
                entry["remaining_qty"] = _as_float(entry["remaining_qty"]) - matched_qty
                remaining_exit_qty -= matched_qty
                if _as_float(entry["remaining_qty"]) <= 1e-9:
                    open_entries[key].pop(0)

        trade_rows.sort(key=lambda item: item["exit_time"] or datetime.min.replace(tzinfo=UTC), reverse=True)
        return trade_rows

    def _best_strategy_name(self, strategy_metrics: dict[str, dict[str, object]]) -> str | None:
        leaderboard = self._leaderboard(strategy_metrics)
        if not leaderboard:
            return None
        return str(leaderboard[0]["strategy_name"])

    def _strategy_strip(self, strategy_metrics: dict[str, dict[str, object]]) -> list[dict[str, object]]:
        items = sorted(
            strategy_metrics.values(),
            key=lambda item: (int(item["active_session_count"]), _as_float(item["return_pct"])),
            reverse=True,
        )
        return [
            {
                "strategy_id": item["strategy_id"],
                "label": item["strategy_name"],
                "sessions": item["active_session_count"],
                "return_pct": item["return_pct"],
                "tone": "success" if _as_float(item["return_pct"]) >= 0 else "danger",
            }
            for item in items[:10]
        ]

    def _market_strip(
        self,
        universe_rows: list[dict[str, object]],
        active_symbols: list[str],
        risk_blocked_symbols: set[str],
    ) -> list[dict[str, object]]:
        rows = sorted(
            universe_rows,
            key=lambda item: (_as_float(item.get("turnover_24h_krw")), _as_float(item.get("surge_score"))),
            reverse=True,
        )
        return [
            {
                "symbol": str(item.get("symbol", "")),
                "selected": bool(item.get("selected", True)),
                "is_active": str(item.get("symbol", "")) in active_symbols,
                "risk_blocked": str(item.get("symbol", "")) in risk_blocked_symbols,
            }
            for item in rows[:12]
        ]

    def _performance_history(
        self,
        derived_trades: list[dict[str, object]],
        strategy_metrics: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        trades_by_strategy: dict[str, list[dict[str, object]]] = defaultdict(list)
        for trade in sorted(derived_trades, key=lambda item: item["exit_time"] or datetime.min.replace(tzinfo=UTC)):
            strategy_id = str(trade["strategy_id"])
            trades_by_strategy[strategy_id].append(trade)

        series: list[dict[str, object]] = []
        palette = ["#22E76B", "#4DA3FF", "#F5B942", "#FF5A5F", "#B388FF", "#7CFFB2"]
        for index, item in enumerate(
            sorted(strategy_metrics.values(), key=lambda row: (_as_float(row["return_pct"]), int(row["active_session_count"])), reverse=True)[:6]
        ):
            strategy_id = str(item["strategy_id"])
            initial_capital = _as_float(item["initial_capital"])
            current_return = _as_float(item["return_pct"])
            running_return = 0.0
            points: list[dict[str, object]] = []
            for trade in trades_by_strategy.get(strategy_id, []):
                trade_exit = trade["exit_time"]
                if not isinstance(trade_exit, datetime):
                    continue
                running_return += ((_as_float(trade["pnl"]) / initial_capital) * 100) if initial_capital > 0 else 0.0
                points.append(
                    {
                        "label": trade_exit.strftime("%m/%d"),
                        "timestamp": trade_exit,
                        "value": round(running_return, 2),
                    }
                )

            if not points:
                points = [
                    {"label": "시작", "timestamp": None, "value": 0.0},
                    {"label": "현재", "timestamp": None, "value": round(current_return, 2)},
                ]
            else:
                points.append(
                    {
                        "label": "현재",
                        "timestamp": None,
                        "value": round(current_return, 2),
                    }
                )

            series.append(
                {
                    "strategy_id": strategy_id,
                    "strategy_name": item["strategy_name"],
                    "color": palette[index % len(palette)],
                    "return_pct": round(current_return, 2),
                    "points": points[-8:],
                }
            )

        return {
            "series": series,
            "best_strategy_name": self._best_strategy_name(strategy_metrics),
        }

    def _live_activity(
        self,
        signals: list[object],
        orders: list[Order],
        risk_events: list[object],
        version_cache: dict[str, object],
        strategy_by_id: dict[str, Strategy],
    ) -> list[dict[str, object]]:
        feed: list[dict[str, object]] = []

        for signal in signals:
            version = version_cache.get(signal.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            strategy_name = strategy_by_id.get(strategy_id).name if strategy_id in strategy_by_id else signal.strategy_version_id
            confidence = _as_float(getattr(signal, "confidence", 0.0)) * 100
            feed.append(
                {
                    "id": f"signal:{signal.id}",
                    "kind": "signal",
                    "strategy_name": strategy_name,
                    "symbol": signal.symbol,
                    "title": f"{signal.symbol} {signal.action.lower()} signal",
                    "detail": f"신뢰도 {confidence:.1f}% · {'차단됨' if signal.blocked else '실행 가능'}",
                    "occurred_at": signal.snapshot_time,
                    "tone": "warning" if signal.blocked else ("success" if signal.action == "ENTER" else "info"),
                }
            )

        for order in orders:
            if order.filled_at is None or order.order_state != OrderState.FILLED or order.executed_price is None:
                continue
            version = version_cache.get(order.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            strategy_name = strategy_by_id.get(strategy_id).name if strategy_id in strategy_by_id else order.strategy_version_id
            feed.append(
                {
                    "id": f"order:{order.id}",
                    "kind": "order",
                    "strategy_name": strategy_name,
                    "symbol": order.symbol,
                    "title": f"{order.symbol} {order.order_role.lower()} fill",
                    "detail": f"{order.executed_qty:.4f} @ {order.executed_price:,.0f}",
                    "occurred_at": order.filled_at,
                    "tone": "success" if order.order_role == "ENTRY" else "info",
                }
            )

        for event in risk_events:
            version = version_cache.get(event.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            strategy_name = strategy_by_id.get(strategy_id).name if strategy_id in strategy_by_id else event.strategy_version_id
            feed.append(
                {
                    "id": f"risk:{event.id}",
                    "kind": "risk",
                    "strategy_name": strategy_name,
                    "symbol": event.symbol,
                    "title": event.message,
                    "detail": event.code,
                    "occurred_at": event.created_at,
                    "tone": "danger" if str(event.severity).upper() in {"CRITICAL", "HIGH", "ERROR"} else "warning",
                }
            )

        feed.sort(key=lambda item: item["occurred_at"] or datetime.min.replace(tzinfo=UTC), reverse=True)
        return feed[:12]

    def _recent_trades(
        self,
        orders: list[Order],
        version_cache: dict[str, object],
        strategy_by_id: dict[str, Strategy],
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for order in orders:
            if order.order_state != OrderState.FILLED or order.filled_at is None or order.executed_price is None:
                continue
            version = version_cache.get(order.strategy_version_id)
            strategy_id = getattr(version, "strategy_id", None)
            strategy_name = strategy_by_id.get(strategy_id).name if strategy_id in strategy_by_id else order.strategy_version_id
            rows.append(
                {
                    "id": order.id,
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_name,
                    "symbol": order.symbol,
                    "order_role": order.order_role,
                    "price": order.executed_price,
                    "qty": order.executed_qty,
                    "filled_at": order.filled_at,
                    "session_id": order.session_id,
                }
            )
        rows.sort(key=lambda item: item["filled_at"] or datetime.min.replace(tzinfo=UTC), reverse=True)
        return rows[:50]

    def _leaderboard(self, strategy_metrics: dict[str, dict[str, object]]) -> list[dict[str, object]]:
        rows = []
        for item in strategy_metrics.values():
            rows.append(
                {
                    "strategy_id": item["strategy_id"],
                    "strategy_name": item["strategy_name"],
                    "strategy_type": item["strategy_type"],
                    "active_session_count": item["active_session_count"],
                    "account_value": round(_as_float(item["account_value"]), 2),
                    "realized_pnl": round(_as_float(item["realized_pnl"]), 2),
                    "unrealized_pnl": round(_as_float(item["unrealized_pnl"]), 2),
                    "return_pct": round(_as_float(item["return_pct"]), 2),
                    "win_rate_pct": round(_as_float(item["win_rate_pct"]), 2) if item["win_rate_pct"] is not None else None,
                    "trades": int(item["trades"]),
                    "risk_alert_count": int(item["risk_alert_count"]),
                }
            )
        rows.sort(
            key=lambda item: (
                _as_float(item["return_pct"]),
                _as_float(item["account_value"]),
                int(item["active_session_count"]),
            ),
            reverse=True,
        )
        return rows

    def _strategy_details(self, strategy_metrics: dict[str, dict[str, object]]) -> list[dict[str, object]]:
        rows = []
        for item in self._leaderboard(strategy_metrics):
            metrics = strategy_metrics[str(item["strategy_id"])]
            rows.append(
                {
                    **item,
                    "paper_session_count": metrics["paper_session_count"],
                    "live_session_count": metrics["live_session_count"],
                    "active_position_count": metrics["active_position_count"],
                    "degraded_session_count": metrics["degraded_session_count"],
                    "monitoring_state": metrics["monitoring_state"],
                    "tracked_symbols": metrics["tracked_symbols"][:4],
                    "last_signal_at": metrics["last_signal_at"],
                    "description": metrics["description"],
                    "open_positions": metrics["open_positions"],
                }
            )
        return rows

    def _market_details(
        self,
        universe_rows: list[dict[str, object]],
        active_symbols_by_session: dict[str, list[str]],
        open_position_symbols: set[str],
        recent_signal_symbols: set[str],
        risk_blocked_symbols: set[str],
    ) -> list[dict[str, object]]:
        return [
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
            for item in sorted(
                universe_rows,
                key=lambda row: (_as_float(row.get("turnover_24h_krw")), _as_float(row.get("surge_score"))),
                reverse=True,
            )
        ]


def _as_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0
