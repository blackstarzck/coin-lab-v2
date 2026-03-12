from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _assert_trace_and_timestamp(body: dict[str, object]) -> None:
    trace_id = body.get("trace_id")
    assert isinstance(trace_id, str)
    assert trace_id.startswith("trc_")

    timestamp = body.get("timestamp")
    assert isinstance(timestamp, str)
    _ = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def test_tc_api_001_strategy_list_response_shape() -> None:
    response = client.get("/api/v1/strategies")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    _assert_trace_and_timestamp(body)

    meta = body.get("meta")
    assert isinstance(meta, dict)
    assert meta["page"] == 1
    assert isinstance(meta["total"], int)
    assert meta["total"] >= 1

    for item in body["data"]:
        assert isinstance(item, dict)
        assert "id" in item
        assert "strategy_key" in item
        assert "name" in item
        assert "strategy_type" in item
        assert "is_active" in item
        assert "created_at" in item


def test_tc_api_001b_strategy_detail_response_shape() -> None:
    response = client.get("/api/v1/strategies/stg_001")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, dict)
    assert data["id"] == "stg_001"
    assert isinstance(data["name"], str)
    assert data["strategy_type"] in {"dsl", "plugin", "hybrid"}


def test_tc_api_002_validation_error_payload_shape() -> None:
    response = client.post("/api/v1/strategies", json={})

    assert response.status_code in {400, 422}
    body = response.json()
    if response.status_code == 422:
        assert isinstance(body.get("detail"), list)
        assert len(body["detail"]) >= 1
    else:
        assert isinstance(body.get("error_code"), str)
        assert isinstance(body.get("message"), str)


def test_tc_api_003_pagination_consistency() -> None:
    page_1_response = client.get("/api/v1/strategies", params={"page": 1, "page_size": 1})
    page_2_response = client.get("/api/v1/strategies", params={"page": 2, "page_size": 1})

    assert page_1_response.status_code == 200
    assert page_2_response.status_code == 200

    page_1_body = page_1_response.json()
    page_2_body = page_2_response.json()

    page_1_data = page_1_body["data"]
    page_2_data = page_2_body["data"]
    assert isinstance(page_1_data, list)
    assert isinstance(page_2_data, list)
    assert len(page_1_data) == 1
    assert len(page_2_data) == 1
    assert page_1_data[0]["id"] != page_2_data[0]["id"]

    page_1_meta = page_1_body.get("meta")
    page_2_meta = page_2_body.get("meta")
    assert isinstance(page_1_meta, dict)
    assert isinstance(page_2_meta, dict)
    assert page_1_meta["total"] == page_2_meta["total"]
    assert page_1_meta["has_next"] is True


def test_tc_api_004_session_create_uses_single_strategy_version_id() -> None:
    payload = {
        "strategy_version_id": "stv_001",
        "mode": "PAPER",
        "symbol_scope": {"symbols": ["KRW-BTC"]},
    }

    response = client.post("/api/v1/sessions", json=payload)

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert isinstance(data, dict)
    assert data["strategy_version_id"] == "stv_001"
    assert data["mode"] == "PAPER"
    assert data["status"] in {"PENDING", "RUNNING"}


def test_tc_api_002b_not_found_error_shape() -> None:
    response = client.get("/api/v1/strategies/nonexistent_999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert isinstance(body.get("error_code"), str)
    assert isinstance(body.get("message"), str)
    assert isinstance(body.get("trace_id"), str)
    assert isinstance(body.get("timestamp"), str)
