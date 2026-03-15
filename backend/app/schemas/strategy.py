from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    strategy_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    strategy_type: Literal["dsl", "plugin", "hybrid"]
    description: str | None = None
    labels: list[str] = Field(default_factory=list)


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None
    labels: list[str] | None = None


class StrategyResponse(BaseModel):
    id: str
    strategy_key: str
    name: str
    strategy_type: Literal["dsl", "plugin", "hybrid"]
    description: str | None
    is_active: bool
    latest_version_id: str | None
    latest_version_no: int | None
    labels: list[str]
    last_7d_return_pct: float | None = None
    last_7d_win_rate: float | None = None
    created_at: datetime
    updated_at: datetime


class StrategyVersionCreate(BaseModel):
    schema_version: str
    config_json: dict[str, object]
    labels: list[str] = Field(default_factory=list)
    notes: str | None = None


class StrategyVersionResponse(BaseModel):
    id: str
    strategy_id: str
    version_no: int
    schema_version: str
    config_hash: str
    labels: list[str]
    notes: str | None = None
    is_validated: bool
    created_at: datetime


class ValidateRequest(BaseModel):
    strict: bool = True


class DraftValidateRequest(ValidateRequest):
    config_json: dict[str, object]


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[dict[str, str]] = Field(default_factory=list)


class StrategyCreateRequest(StrategyCreate):
    pass

class StrategyUpdateRequest(StrategyUpdate):
    pass

class StrategyVersionCreateRequest(StrategyVersionCreate):
    pass

class ValidateStrategyVersionRequest(ValidateRequest):
    pass

class ValidateStrategyVersionResponse(ValidateResponse):
    pass


ExplainValue = float | int | bool | str | None


class ExplainFact(BaseModel):
    label: str
    value: ExplainValue


class ExplainPayload(BaseModel):
    snapshot_key: str
    decision: str
    reason_codes: list[str] = Field(default_factory=list)
    facts: list[ExplainFact] = Field(default_factory=list)
    parameters: list[ExplainFact] = Field(default_factory=list)
    matched_conditions: list[str] = Field(default_factory=list)
    failed_conditions: list[str] = Field(default_factory=list)
    risk_blocks: list[str] = Field(default_factory=list)
    legacy_payload: bool = False
    legacy_note: str | None = None
