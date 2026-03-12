from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.application import container as container_module
from app.application.container import Container, get_container
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.main import app


@pytest.fixture(autouse=True)
def isolate_app_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force API tests onto the in-memory store so they never write into Supabase."""
    monkeypatch.setenv("COIN_LAB_APP_ENV", "test")
    monkeypatch.setenv("COIN_LAB_STORE_BACKEND", "memory")
    monkeypatch.delenv("COIN_LAB_DATABASE_URL", raising=False)
    container_module._container = None
    yield
    container_module._container = None


@pytest.fixture()
def store() -> InMemoryLabStore:
    """Fresh InMemoryLabStore seeded with defaults."""
    s = InMemoryLabStore()
    s.seed_defaults()
    return s


@pytest.fixture()
def client() -> TestClient:
    """FastAPI TestClient backed by InMemoryLabStore (default)."""
    return TestClient(app)


@pytest.fixture()
def container() -> Container:
    """Return the singleton container used by the app."""
    return get_container()
