from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        trace_id = getattr(record, "trace_id", None)
        if isinstance(trace_id, str):
            payload["trace_id"] = trace_id
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(level: str) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Silence noisy third-party loggers in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
