from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.repositories.lab_store import LabStore


class RuntimeService:
    def __init__(self, settings: Settings, store: LabStore) -> None:
        self.settings = settings
        self.store = store
        self.running = False

    def status(self) -> dict[str, object]:
        sessions = self.store.list_sessions()
        running_count = len([item for item in sessions if str(getattr(item.status, "value", item.status)) == "RUNNING"])
        return {
            "running": self.running,
            "store_backend": self.settings.store_backend,
            "session_count": len(sessions),
            "running_session_count": running_count,
        }

    def start(self) -> dict[str, object]:
        self.running = True
        return {"accepted": True, "status": "started"}

    def stop(self) -> dict[str, object]:
        self.running = False
        return {"accepted": True, "status": "stopped"}
