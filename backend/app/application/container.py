from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from ..core.config import Settings, load_settings
from ..infrastructure.repositories.lab_store import LabStore


@dataclass(slots=True)
class Container:
    settings: Settings
    store: LabStore
    strategy_service: Any
    session_service: Any
    backtest_service: Any
    monitoring_service: Any
    log_service: Any
    universe_service: Any
    stream_service: Any
    health_service: Any
    strategy_validator: Any
    execution_service: Any
    risk_guard_service: Any
    fill_engine: Any
    signal_generator: Any
    runtime_service: Any
    market_ingest_service: Any

    @classmethod
    def build(cls) -> "Container":
        backtest_module = importlib.import_module("app.application.services.backtest_service")
        execution_module = importlib.import_module("app.application.services.execution_service")
        fill_engine_module = importlib.import_module("app.application.services.fill_engine")
        health_module = importlib.import_module("app.application.services.health_service")
        log_module = importlib.import_module("app.application.services.log_service")
        market_ingest_module = importlib.import_module("app.application.services.market_ingest_service")
        monitoring_module = importlib.import_module("app.application.services.monitoring_service")
        runtime_module = importlib.import_module("app.application.services.runtime_service")
        risk_guard_module = importlib.import_module("app.application.services.risk_guard_service")
        session_module = importlib.import_module("app.application.services.session_service")
        signal_generator_module = importlib.import_module("app.application.services.signal_generator")
        stream_module = importlib.import_module("app.application.services.stream_service")
        strategy_module = importlib.import_module("app.application.services.strategy_service")
        strategy_validator_module = importlib.import_module("app.application.services.strategy_validator")
        universe_module = importlib.import_module("app.application.services.universe_service")

        BacktestService = getattr(backtest_module, "BacktestService")
        ExecutionService = getattr(execution_module, "ExecutionService")
        FillEngine = getattr(fill_engine_module, "FillEngine")
        HealthService = getattr(health_module, "HealthService")
        LogService = getattr(log_module, "LogService")
        MarketIngestService = getattr(market_ingest_module, "MarketIngestService")
        MonitoringService = getattr(monitoring_module, "MonitoringService")
        RuntimeService = getattr(runtime_module, "RuntimeService")
        RiskGuardService = getattr(risk_guard_module, "RiskGuardService")
        SessionService = getattr(session_module, "SessionService")
        SignalGenerator = getattr(signal_generator_module, "SignalGenerator")
        StreamService = getattr(stream_module, "StreamService")
        StrategyService = getattr(strategy_module, "StrategyService")
        StrategyValidator = getattr(strategy_validator_module, "StrategyValidator")
        UniverseService = getattr(universe_module, "UniverseService")

        settings = load_settings()
        store: LabStore
        if settings.store_backend == "postgres":
            if not settings.database_url:
                raise RuntimeError("COIN_LAB_DATABASE_URL is required when STORE_BACKEND=postgres")
            pg_module = importlib.import_module("app.infrastructure.repositories.postgres_lab_store")
            PostgresLabStore = getattr(pg_module, "PostgresLabStore")
            store = PostgresLabStore(settings.database_url)
        else:
            mem_module = importlib.import_module("app.infrastructure.repositories.in_memory_lab_store")
            InMemoryLabStore = getattr(mem_module, "InMemoryLabStore")
            store = InMemoryLabStore()
        store.seed_defaults()
        strategy_validator = StrategyValidator()
        risk_guard_service = RiskGuardService()
        fill_engine = FillEngine()
        signal_generator = SignalGenerator()
        execution_service = ExecutionService(risk_guard_service, fill_engine, signal_generator)
        market_ingest_service = MarketIngestService()
        stream_service = StreamService(store)
        runtime_service = RuntimeService(settings, store, stream_service, market_ingest_service, execution_service)
        return cls(
            settings=settings,
            store=store,
            strategy_service=StrategyService(store, strategy_validator),
            session_service=SessionService(store, settings, stream_service),
            backtest_service=BacktestService(store),
            monitoring_service=MonitoringService(store),
            log_service=LogService(store),
            universe_service=UniverseService(store),
            stream_service=stream_service,
            health_service=HealthService(settings, store),
            strategy_validator=strategy_validator,
            execution_service=execution_service,
            risk_guard_service=risk_guard_service,
            fill_engine=fill_engine,
            signal_generator=signal_generator,
            runtime_service=runtime_service,
            market_ingest_service=market_ingest_service,
        )


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container.build()
    return _container
