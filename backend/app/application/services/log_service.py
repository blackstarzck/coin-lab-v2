from __future__ import annotations

from ...infrastructure.repositories.lab_store import LabStore


class LogService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def list_channel_logs(self, channel: str, session_id: str | None, limit: int) -> list[dict[str, object]]:
        rows = self.store.query_logs(channel=channel, session_id=session_id, limit=limit)
        return [
            {
                "id": item.id,
                "channel": item.channel,
                "level": item.level,
                "trace_id": item.trace_id,
                "mode": item.mode,
                "session_id": item.session_id,
                "strategy_version_id": item.strategy_version_id,
                "symbol": item.symbol,
                "event_type": item.event_type,
                "message": item.message,
                "payload": item.payload,
                "logged_at": item.logged_at,
            }
            for item in rows
        ]
