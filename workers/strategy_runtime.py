from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _backend_path() -> Path:
    return Path(__file__).resolve().parents[1] / "backend"


sys.path.insert(0, str(_backend_path()))

from app.application.container import get_container  # noqa: E402


def _serialize(value: object) -> object:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger a manual runtime reevaluation for a running session.")
    parser.add_argument("--session-id", required=True, help="Session identifier to reevaluate.")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols to reevaluate. Defaults to the session active scope.")
    args = parser.parse_args()

    container = get_container()
    session = container.session_service.get_session(args.session_id)
    symbols = [symbol.strip() for symbol in str(args.symbols).split(",") if symbol.strip()]
    result = container.runtime_service.manual_reevaluate_session(session, symbols=symbols or None)
    print(json.dumps(result, ensure_ascii=False, default=_serialize))


if __name__ == "__main__":
    main()
