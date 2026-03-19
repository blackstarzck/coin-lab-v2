from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _backend_path() -> Path:
    return Path(__file__).resolve().parents[1] / "backend"


sys.path.insert(0, str(_backend_path()))

from app.application.container import get_container  # noqa: E402
from app.schemas.backtest import BacktestRunRequest  # noqa: E402


def _serialize(value: object) -> object:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Coin Lab backtest payload through the application container.")
    parser.add_argument("--payload-file", required=True, help="Path to a JSON file compatible with BacktestRunRequest.")
    args = parser.parse_args()

    payload_path = Path(args.payload_file).resolve()
    request = BacktestRunRequest.model_validate_json(payload_path.read_text(encoding="utf-8"))
    result = get_container().backtest_service.run_backtest(request)
    print(json.dumps(result, ensure_ascii=False, default=_serialize))


if __name__ == "__main__":
    main()
