from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.application.container import Container, get_container
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.infrastructure.repositories.lab_store import LabStore
from app.main import app


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
