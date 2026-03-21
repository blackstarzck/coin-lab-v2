from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.session import SessionCreate

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


def test_tc_api_001c_plugin_catalog_response_shape() -> None:
    response = client.get("/api/v1/strategies/plugins")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    _assert_trace_and_timestamp(body)

    plugin_ids = {item["plugin_id"] for item in body["data"]}
    assert {"breakout_v1", "smc_confluence_v1", "ob_fvg_bull_reclaim_v1", "zenith_hazel_v1"}.issubset(plugin_ids)

    ob_fvg = next(item for item in body["data"] if item["plugin_id"] == "ob_fvg_bull_reclaim_v1")
    assert ob_fvg["label"] == "OB FVG Bull Reclaim V1"
    assert isinstance(ob_fvg["default_config"], dict)
    assert ob_fvg["default_config"]["timeframe"] == "15m"
    assert isinstance(ob_fvg["fields"], list)
    assert any(field["key"] == "trend_timeframe" for field in ob_fvg["fields"])

    zenith = next(item for item in body["data"] if item["plugin_id"] == "zenith_hazel_v1")
    assert zenith["label"] == "Zenith Hazel V1"
    assert isinstance(zenith["default_config"], dict)
    assert zenith["default_config"]["regime_timeframe"] == "1h"
    assert isinstance(zenith["fields"], list)
    assert any(field["key"] == "volume_surge_ratio" for field in zenith["fields"])


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


def test_tc_api_004c_session_manual_reevaluate_response_shape(client: TestClient, container, monkeypatch) -> None:
    session = container.session_service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"symbols": ["KRW-BTC"]},
        )
    )
    monkeypatch.setattr(
        container.runtime_service,
        "manual_reevaluate_session",
        lambda current_session, symbols=None: {
            "accepted": True,
            "session_id": current_session.id,
            "requested_symbols": symbols or ["KRW-BTC"],
            "evaluated_symbols": ["KRW-BTC"],
            "skipped": [],
        },
    )

    response = client.post(f"/api/v1/sessions/{session.id}/reevaluate", json={"symbols": ["KRW-BTC"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    _assert_trace_and_timestamp(body)
    data = body["data"]
    assert data["accepted"] is True
    assert data["session_id"] == session.id
    assert data["requested_symbols"] == ["KRW-BTC"]
    assert data["evaluated_symbols"] == ["KRW-BTC"]
    assert data["skipped"] == []


def test_tc_api_005_universe_catalog_response_shape(client: TestClient, container, monkeypatch) -> None:
    monkeypatch.setattr(
        container.universe_service,
        "catalog",
        lambda quote="KRW", query=None, limit=10: [
            {
                "symbol": "KRW-BTC",
                "korean_name": "비트코인",
                "english_name": "Bitcoin",
                "market_warning": "NONE",
                "turnover_24h_krw": 900_000_000_000,
                "trade_price": 150_000_000,
            }
        ][:limit],
    )

    response = client.get("/api/v1/universe/catalog", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    _assert_trace_and_timestamp(body)
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    item = body["data"][0]
    assert item["symbol"] == "KRW-BTC"
    assert isinstance(item["korean_name"], str)
    assert isinstance(item["english_name"], str)
    assert isinstance(item["turnover_24h_krw"], (int, float))


def test_tc_api_002b_not_found_error_shape() -> None:
    response = client.get("/api/v1/strategies/nonexistent_999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert isinstance(body.get("error_code"), str)
    assert isinstance(body.get("message"), str)
    assert isinstance(body.get("trace_id"), str)
    assert isinstance(body.get("timestamp"), str)
