from __future__ import annotations

from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import api_router
from .api.ws_router import ws_router
from .application.container import get_container
from .core.config import load_settings
from .core.exceptions import CoinLabError
from .core.logging import get_logger, setup_logging
from .core.trace import generate_trace_id, utc_now_iso


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    settings = load_settings()
    setup_logging(settings.log_level)
    logger = get_logger("app")
    logger.info("Starting Coin Lab API...")
    get_container()
    yield
    logger.info("Shutting down Coin Lab API...")


_settings = load_settings()
_is_production = _settings.app_env == "production"

app = FastAPI(
    title="Coin Lab API",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(ws_router)


@app.exception_handler(CoinLabError)
async def app_error_handler(request: Request, exc: CoinLabError) -> JSONResponse:
    _ = request
    error_code = exc.error_code.value if isinstance(exc.error_code, Enum) else str(exc.error_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": error_code,
            "message": exc.message,
            "details": exc.details if not _is_production else {},
            "trace_id": generate_trace_id(),
            "timestamp": utc_now_iso(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    _ = request
    logger = get_logger("app")
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "Internal server error" if _is_production else str(exc),
            "details": {},
            "trace_id": generate_trace_id(),
            "timestamp": utc_now_iso(),
        },
    )
