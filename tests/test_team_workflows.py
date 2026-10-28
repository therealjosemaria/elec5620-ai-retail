"""Cross-feature API tests over the shared SQLite data, without model calls."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from backend.main import SAMPLE, create_app, fixture_extract

HEADERS = {"Authorization": "Bearer test-operator"}


@pytest.fixture
def system(tmp_path):
    path = tmp_path / "db"
    calls = []
    def extract(text):
        calls.append(text)
        return fixture_extract(SAMPLE)
    with TestClient(create_app(path, "fixture", extractor=extract, operator_token="test-operator")) as client:
        yield client, path, calls


def capture(client, text=SAMPLE):
    response = client.post("/api/requests", json={"request_id": str(uuid4()), "text": text})
    assert response.status_code == 201
    return response.json()["request_id"]


def dump(path):
    with sqlite3.connect(path) as db:
        # Result/trace persistence is intentional; business source rows stay unchanged.
        return [line for line in db.iterdump() if not any(
            f'INSERT INTO "{table}"' in line for table in ("recommendation_results", "workflow_runs"))]


def test_capture_recommend_filter_availability_share_data_without_additional_model_calls(system):
    client, path, calls = system
    rid = capture(client)
    before = dump(path)
    rec = client.post(f"/api/requests/{rid}/recommendations").json()
    assert [r["product"]["product_id"] for r in rec["recommendations"]] == ["product-001", "product-002"]
    budget = client.get(f"/api/requests/{rid}/budget-filter")
    assert budget.status_code == 200
    assert [p["product_id"] for p in budget.json()["products"]] == ["product-001"]
    assert budget.json()["excluded_product_ids"] == ["product-002"]
    assert all(Decimal(p["price"]) <= Decimal(budget.json()["budget"]) for p in budget.json()["products"])
    available = client.get(f"/api/requests/{rid}/availability?within_budget=true")
    assert available.status_code == 200
    assert available.json()[0]["status"] == "Available"
    assert available.json()[0]["stock_quantity"] == 24
    assert len(client.get(f"/api/requests/{rid}/availability").json()) == 2
    assert calls == [SAMPLE]
    assert dump(path) == before


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP", "US dollars", "Canadian dollars"])
def test_foreign_currency_is_not_silently_treated_as_aud(system, currency):
    client, _, _ = system
    rid = capture(client, SAMPLE + " Currency: " + currency)
    assert client.post(f"/api/requests/{rid}/recommendations").status_code == 200
    response = client.get(f"/api/requests/{rid}/budget-filter")
    assert response.status_code == 422 and "Only AUD" in response.text


def test_operator_endpoints_deny_before_returning_any_data(system):
    client, path, calls = system
    before = dump(path)
    for url, body in [("/api/profit-margins", {"product_id": "product-001"}),
                      ("/api/restocking-priorities", {"product_id": "product-003"}),
                      ("/api/inventory/availability", {"product_ids": ["product-001"]})]:
        assert client.post(url, json=body).status_code == 403
        assert client.post(url, json=body, headers={"Authorization": "Bearer wrong"}).status_code == 403
    assert calls == [] and dump(path) == before


def test_profit_summary_and_missing_cost_coverage(system):
    client, path, calls = system
    before = dump(path)
    result = client.post("/api/profit-margins", json={"product_id": "product-001"}, headers=HEADERS)
    assert result.status_code == 200 and result.json()["outcome"] == "complete"
    assert Decimal(result.json()["revenue"]) > 0
    partial = client.post("/api/profit-margins", json={"product_id": "product-002"}, headers=HEADERS).json()
    assert partial["outcome"] == "partial" and partial["excluded_missing_cost"] == 1
    invalid = client.post("/api/profit-margins", json={}, headers=HEADERS).json()
    assert invalid["outcome"] == "invalid_scope" and invalid["revenue"] is None
    assert calls == [] and dump(path) == before


def test_profit_never_includes_unfinished_sales(system):
    client, path, _ = system
    before = client.post("/api/profit-margins", json={"product_id": "product-001"}, headers=HEADERS).json()
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO sales (product_id,sale_date,quantity,selling_price,cost) VALUES (?, ?, ?, ?, ?)",
                   ("product-001", (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat(), 999, "999", "1"))
    after = client.post("/api/profit-margins", json={"product_id": "product-001"}, headers=HEADERS).json()
    assert after["revenue"] == before["revenue"] and after["record_count"] == before["record_count"]


def test_restocking_uses_shared_stock_and_completed_sales(system):
    client, path, calls = system
    before = dump(path)
    result = client.post("/api/restocking-priorities", json={"product_id": "product-003"}, headers=HEADERS).json()
    assert result["outcome"] == "presented" and result["data_mode"] == "sqlite_prototype"
    assert result["priorities"][0]["stock_quantity"] == 3
    assert result["priorities"][0]["sold_quantity"] > 0
    assert client.post("/api/restocking-priorities", json={"product_id": "product-001"}, headers=HEADERS).json()["outcome"] == "no_priority"
    assert client.post("/api/restocking-priorities", json={"product_id": "product-005"}, headers=HEADERS).json()["outcome"] == "data_error"
    assert calls == [] and dump(path) == before


def test_availability_current_zero_stale_missing_and_source_failure(system):
    client, path, _ = system
    response = client.post("/api/inventory/availability", json={"product_ids": [
        "product-001", "product-004", "product-005", "product-006"]}, headers=HEADERS)
    assert response.status_code == 200
    assert [r["status"] for r in response.json()] == ["Available", "Unavailable", "Unknown", "Unknown"]
    assert client.post("/api/inventory/availability", json={"product_ids": []}, headers=HEADERS).status_code == 400
    assert client.post("/api/inventory/availability", json={"product_ids": ["bad/id", " "]}, headers=HEADERS).status_code == 400
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE inventory_items")
    outage = client.post("/api/inventory/availability", json={"product_ids": ["product-001"]}, headers=HEADERS)
    assert outage.status_code == 503


def test_profit_source_unavailable_returns_no_financial_values(system):
    client, path, _ = system
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE sales")
    response = client.post("/api/profit-margins", json={"product_id": "product-001"}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["outcome"] == "source_unavailable"
    assert response.json()["revenue"] is None and response.json()["profit"] is None


def test_budget_missing_and_empty_candidates_are_explicit(tmp_path):
    for amount, expected in [(None, 422), ("under $1", 200)]:
        text = "red wine under $1"
        evidence = dict(budget=amount, party_size=None, occasion=None, taste_preferences=["red wine"], constraints=[])
        with TestClient(create_app(tmp_path / str(uuid4()), "fixture", extractor=lambda _: json.dumps(evidence))) as client:
            rid = capture(client, text)
            assert client.post(f"/api/requests/{rid}/recommendations").status_code == 200
            result = client.get(f"/api/requests/{rid}/budget-filter")
            assert result.status_code == expected
            if expected == 200:
                assert result.json()["status"] == "NoMatch" and result.json()["products"] == []
            else:
                assert client.get(f"/api/requests/{rid}/availability").status_code == 200
