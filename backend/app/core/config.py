from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _load_dotenv(path: str | os.PathLike[str] | None = None) -> None:
    dotenv_path = Path(path).resolve() if path is not None else default_env_file()
    try:
        module = importlib.import_module("dotenv")
    except ModuleNotFoundError:
        return
    load_dotenv = getattr(module, "load_dotenv", None)
    if callable(load_dotenv):
        load_dotenv(str(dotenv_path))


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_origins(value: str | None) -> list[str]:
    if value is None:
        return ["http://localhost:5173"]
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return ["http://localhost:5173"]
    if not isinstance(parsed, list):
        return ["http://localhost:5173"]
    return [str(item) for item in parsed]


@dataclass(slots=True)
class Settings:
    app_env: str
    log_level: str
    allowed_origins: list[str]
    store_backend: str
    database_url: str | None
    upbit_rest_base_url: str
    upbit_ws_public_url: str
    upbit_ws_private_url: str
    upbit_access_key: str | None
    upbit_secret_key: str | None
    live_trading_enabled: bool
    live_require_order_test: bool
    live_order_notional_krw: int


def load_settings(env_file: str | os.PathLike[str] | None = None) -> Settings:
    _load_dotenv(env_file)
    return Settings(
        app_env=os.getenv("COIN_LAB_APP_ENV", "development"),
        log_level=os.getenv("COIN_LAB_LOG_LEVEL", "INFO"),
        allowed_origins=_parse_origins(os.getenv("COIN_LAB_ALLOWED_ORIGINS")),
        store_backend=os.getenv("COIN_LAB_STORE_BACKEND", "memory"),
        database_url=os.getenv("COIN_LAB_DATABASE_URL"),
        upbit_rest_base_url=os.getenv("COIN_LAB_UPBIT_REST_BASE_URL", "https://api.upbit.com"),
        upbit_ws_public_url=os.getenv("COIN_LAB_UPBIT_WS_PUBLIC_URL", "wss://api.upbit.com/websocket/v1"),
        upbit_ws_private_url=os.getenv(
            "COIN_LAB_UPBIT_WS_PRIVATE_URL",
            "wss://api.upbit.com/websocket/v1/private",
        ),
        upbit_access_key=os.getenv("COIN_LAB_UPBIT_ACCESS_KEY"),
        upbit_secret_key=os.getenv("COIN_LAB_UPBIT_SECRET_KEY"),
        live_trading_enabled=_parse_bool(os.getenv("COIN_LAB_LIVE_TRADING_ENABLED"), default=False),
        live_require_order_test=_parse_bool(os.getenv("COIN_LAB_LIVE_REQUIRE_ORDER_TEST"), default=True),
        live_order_notional_krw=int(os.getenv("COIN_LAB_LIVE_ORDER_NOTIONAL_KRW", "5000")),
    )


get_settings = load_settings
