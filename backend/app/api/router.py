from __future__ import annotations

from fastapi import APIRouter

from .routes.backtests import router as backtests_router
from .routes.health import router as health_router
from .routes.logs import router as logs_router
from .routes.monitoring import router as monitoring_router
from .routes.sessions import router as sessions_router
from .routes.strategies import router as strategies_router
from .routes.strategies import version_router as strategy_versions_router
from .routes.universe import router as universe_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(strategies_router, tags=["Strategies"])
api_router.include_router(strategy_versions_router, tags=["Strategies"])
api_router.include_router(sessions_router, tags=["Sessions"])
api_router.include_router(backtests_router, tags=["Backtests"])
api_router.include_router(monitoring_router, tags=["Monitoring"])
api_router.include_router(logs_router, tags=["Logs"])
api_router.include_router(universe_router, tags=["Universe"])
