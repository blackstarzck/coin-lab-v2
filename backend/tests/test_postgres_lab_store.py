from __future__ import annotations

from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS

from app.infrastructure.repositories.postgres_lab_store import PostgresLabStore


class _FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple[object, bool]] = []

    def putconn(self, conn: object, close: bool = False) -> None:
        self.calls.append((conn, close))


class _FakeConnection:
    def __init__(self, *, closed: bool = False, status: int = TRANSACTION_STATUS_IDLE, rollback_error: Exception | None = None) -> None:
        self.closed = closed
        self._status = status
        self._rollback_error = rollback_error
        self.rollback_calls = 0

    def get_transaction_status(self) -> int:
        return self._status

    def rollback(self) -> None:
        self.rollback_calls += 1
        if self._rollback_error is not None:
            raise self._rollback_error


def _build_store(pool: _FakePool) -> PostgresLabStore:
    store = PostgresLabStore.__new__(PostgresLabStore)
    store._pool = pool
    return store


def test_put_conn_rolls_back_open_transaction_before_returning_to_pool() -> None:
    pool = _FakePool()
    store = _build_store(pool)
    conn = _FakeConnection(status=TRANSACTION_STATUS_INTRANS)

    store._put_conn(conn)

    assert conn.rollback_calls == 1
    assert pool.calls == [(conn, False)]


def test_put_conn_closes_broken_connection_when_cleanup_fails() -> None:
    pool = _FakePool()
    store = _build_store(pool)
    conn = _FakeConnection(status=TRANSACTION_STATUS_INTRANS, rollback_error=RuntimeError("boom"))

    store._put_conn(conn)

    assert conn.rollback_calls == 1
    assert pool.calls == [(conn, True)]
