from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from ...core.exceptions import NotFoundError
from ...domain.entities.strategy import Strategy, StrategyType, StrategyVersion
from ...infrastructure.repositories.lab_store import LabStore
from ...schemas.strategy import StrategyCreate, StrategyUpdate, StrategyVersionCreate
from .strategy_validator import StrategyValidator


def _now() -> datetime:
    return datetime.now(UTC)


class StrategyService:
    def __init__(self, store: LabStore, validator: StrategyValidator) -> None:
        self.store = store
        self.validator = validator

    def list_strategies(
        self,
        is_active: bool | None = None,
        label: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Strategy], int]:
        rows = self.store.list_strategies()
        if is_active is not None:
            rows = [item for item in rows if item.is_active == is_active]
        if label is not None:
            rows = [item for item in rows if label in item.labels]
        total = len(rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return rows[start:end], total

    def get_strategy(self, strategy_id: str) -> Strategy:
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise NotFoundError("Strategy not found", {"strategy_id": strategy_id})
        return strategy

    def get_strategy_version(self, version_id: str) -> StrategyVersion:
        version = self.store.get_strategy_version(version_id)
        if version is None:
            raise NotFoundError("Strategy version not found", {"version_id": version_id})
        return version

    def list_strategy_versions(self, strategy_id: str) -> list[StrategyVersion]:
        self.get_strategy(strategy_id)
        return self.store.list_strategy_versions(strategy_id)

    def create_strategy(self, data: StrategyCreate) -> Strategy:
        now = _now()
        strategy = Strategy(
            id=f"stg_{uuid4().hex[:12]}",
            strategy_key=data.strategy_key,
            name=data.name,
            strategy_type=StrategyType(data.strategy_type),
            description=data.description,
            is_active=True,
            latest_version_id=None,
            latest_version_no=None,
            labels=data.labels,
            created_at=now,
            updated_at=now,
        )
        return self.store.create_strategy(strategy)

    def update_strategy(self, strategy_id: str, data: StrategyUpdate) -> Strategy:
        strategy = self.get_strategy(strategy_id)
        updates = data.model_dump(exclude_none=True)
        if "name" in updates:
            strategy.name = str(updates["name"])
        if "description" in updates:
            description_value = updates["description"]
            strategy.description = str(description_value) if description_value is not None else None
        if "is_active" in updates:
            strategy.is_active = bool(updates["is_active"])
        if "labels" in updates:
            strategy.labels = [str(label) for label in updates["labels"]]
        strategy.updated_at = _now()
        return self.store.update_strategy(strategy)

    def create_version(self, strategy_id: str, data: StrategyVersionCreate) -> StrategyVersion:
        strategy = self.get_strategy(strategy_id)
        versions = self.store.list_strategy_versions(strategy_id)
        config_payload = json.dumps(data.config_json, sort_keys=True, separators=(",", ":"))
        version = StrategyVersion(
            id=f"stv_{uuid4().hex[:12]}",
            strategy_id=strategy_id,
            version_no=len(versions) + 1,
            schema_version=data.schema_version,
            config_json=data.config_json,
            config_hash=f"sha256:{hashlib.sha256(config_payload.encode('utf-8')).hexdigest()}",
            labels=data.labels,
            notes=data.notes,
            is_validated=False,
            validation_summary=None,
            created_by="system",
            created_at=_now(),
        )
        created = self.store.create_strategy_version(version)
        strategy.latest_version_id = created.id
        strategy.latest_version_no = created.version_no
        strategy.updated_at = _now()
        self.store.update_strategy(strategy)
        return created

    def create_strategy_version(self, strategy_id: str, data: StrategyVersionCreate) -> StrategyVersion:
        return self.create_version(strategy_id, data)

    def validate_version(self, version_id: str, strict: bool) -> dict[str, object]:
        version = self.get_strategy_version(version_id)
        result = self.validator.validate(version.config_json, strict)
        version.is_validated = bool(result["valid"])
        version.validation_summary = result
        self.store.update_strategy_version(version)
        return result

    def validate_draft(self, config_json: dict[str, object], strict: bool) -> dict[str, object]:
        return self.validator.validate(config_json, strict)

    def validate_strategy_version(self, version_id: str, strict: bool) -> dict[str, object]:
        return self.validate_version(version_id, strict)
