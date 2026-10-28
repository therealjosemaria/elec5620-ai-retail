"""Traceable cases for UC-M3-01 (report §6.3.1, §10.5, Figures 10/15/20). No model calls."""
from datetime import datetime, timedelta, timezone
import sqlite3
import time

from fastapi.testclient import TestClient
import pytest

from backend.low_stock import ALERT_RULE, AlertOutcome, AlertStatus, evaluate_low_stock
from backend.main import create_app
from backend.models import InventoryItem
from backend.stock import InventoryLookupResult, LookupStatus

NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def found(pid="p1", qty=3, threshold=10, stamp=NOW, status=LookupStatus.FOUND, reason=None):
    item = InventoryItem(inventory_id="inventory-001", product_id=pid, stock_quantity=qty,
                         reorder_threshold=threshold, last_updated=stamp)
    return InventoryLookupResult(product_id=pid, status=status, item=item, reason=reason)


def stale(pid="p1", qty=3, threshold=10):
    return found(pid, qty, threshold, stamp=NOW - timedelta(hours=72), status=LookupStatus.STALE,
                 reason="Inventory record is stale; not confirmed current.")


def unresolved(pid, status, reason):
    return InventoryLookupResult(product_id=pid, status=status, reason=reason)


@pytest.mark.parametrize("qty,threshold,expected", [
    (3, 10, AlertStatus.LOW_STOCK), (10, 10, AlertStatus.LOW_STOCK), (0, 8, AlertStatus.LOW_STOCK),
    (0, 0, AlertStatus.LOW_STOCK), (11, 10, AlertStatus.NOT_REQUIRED),
])
def test_main_flow_alerts_at_or_below_threshold_only(qty, threshold, expected):
    result = evaluate_low_stock([found(qty=qty, threshold=threshold)], now=NOW)
    [item] = result.items
    assert item.status == expected
    assert (item.stock_quantity, item.reorder_threshold, item.last_updated) == (qty, threshold, NOW)
    assert item.suggested_quantity is None  # No reorder calculation (§6.3.1 out of scope).
    assert result.rule == ALERT_RULE


def test_alert_carries_evidence_and_traceable_timestamp():
    result = evaluate_low_stock([found("p1", 3, 10), found("p2", 24, 10)], now=NOW)
    assert result.outcome == AlertOutcome.PRESENTED and result.limitations == []
    low = result.items[0]
    assert low.explanation.startswith("Stock 3 ≤ threshold 10.")
    assert result.model_dump(mode="json")["items"][0]["last_updated"] == "2026-10-28T00:00:00Z"


def test_2b_stale_record_withheld_with_its_evidence():
    result = evaluate_low_stock([stale(qty=1), found("p2", 3, 10)], now=NOW)
    first, second = result.items
    assert first.status == AlertStatus.STALE and first.stock_quantity == 1
    assert first.explanation.endswith("No alert is presented as current.")
    assert second.status == AlertStatus.LOW_STOCK
    assert result.outcome == AlertOutcome.PARTIAL
    assert result.limitations == ["1 stale record(s) withheld; their low-stock status is not presented as current."]


@pytest.mark.parametrize("record", [
    unresolved("p9", LookupStatus.NOT_FOUND, "No inventory record for this product."),
    unresolved("bad id", LookupStatus.ERROR, "Invalid product identifier."),
    unresolved("p1", LookupStatus.ERROR, "Inventory record is incomplete or invalid."),
    found(qty=-1), found(threshold=-1), found(stamp=NOW + timedelta(days=1)), found(stamp=NOW.replace(tzinfo=None)),
])
def test_2a_missing_or_invalid_records_excluded(record):
    result = evaluate_low_stock([record, found("p2", 24, 10)], now=NOW)
    excluded = result.items[0]
    assert excluded.status == AlertStatus.EXCLUDED and excluded.explanation
    if record.status != LookupStatus.FOUND:
        assert excluded.explanation == record.reason
    assert result.outcome == AlertOutcome.PARTIAL
    assert "1 record(s) excluded: missing, unknown or invalid inventory evidence." in result.limitations


@pytest.mark.parametrize("records", [
    [],
    [unresolved("p1", LookupStatus.ERROR, "Inventory source unavailable."),
     unresolved("p2", LookupStatus.ERROR, "Inventory source unavailable.")],
    [stale()],
])
def test_3a_status_undetermined_without_current_evidence(records):
    result = evaluate_low_stock(records, now=NOW)
    assert result.outcome == AlertOutcome.DATA_ERROR
    assert not any(i.status == AlertStatus.LOW_STOCK for i in result.items)
    assert result.limitations[-1] == "Low-stock status cannot be determined from the available inventory evidence."


def test_4a_no_product_meets_threshold():
    result = evaluate_low_stock([found("p1", 24, 10), found("p2", 11, 10)], now=NOW)
    assert result.outcome == AlertOutcome.NOT_REQUIRED and result.limitations == []
    assert {i.status for i in result.items} == {AlertStatus.NOT_REQUIRED}


def test_decision_is_read_only():
    records = [found(), stale("p2")]
    before = [r.model_dump() for r in records]
    evaluate_low_stock(records, now=NOW)
    assert [r.model_dump() for r in records] == before


def test_performance_10000_records_within_5_seconds():
    records = [found(f"p{i}", qty=i % 20, threshold=10) for i in range(10_000)]
    started = time.perf_counter()
    result = evaluate_low_stock(records, now=NOW)
    elapsed = time.perf_counter() - started
    assert len(result.items) == 10_000 and result.outcome == AlertOutcome.PRESENTED
    assert elapsed < 5, f"{elapsed:.2f}s"


@pytest.fixture
def system(tmp_path):
    path = tmp_path / "db"
    with TestClient(create_app(path, "fixture", operator_token="operator")) as client:
        yield client, path, {"Authorization": "Bearer operator"}


def test_api_reports_figure_20_states_over_prototype_inventory(system):
    client, path, headers = system
    with sqlite3.connect(path) as db:
        before = db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall()
    started = time.perf_counter()
    response = client.post("/api/low-stock-alerts", json={}, headers=headers)
    elapsed = time.perf_counter() - started
    body = response.json()
    assert response.status_code == 200 and elapsed < 5
    statuses = {i["product_id"]: i["status"] for i in body["items"]}
    assert statuses == {"product-001": "not_required", "product-002": "low_stock", "product-003": "low_stock",
                        "product-004": "low_stock", "product-005": "stale", "product-006": "excluded"}
    assert body["outcome"] == "partial"
    assert any(step["sender"] == "inventory_procurement_agent" for step in body["trace"])
    saved = client.get(f"/api/workflows/{body['workflow_id']}", headers=headers).json()
    assert saved["inventory_decision"]["items"] == body["items"]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall() == before


def test_reorder_path_is_unchanged(system):
    client, _, headers = system
    reorder = client.post("/api/reorder-suggestions", json={}, headers=headers).json()
    assert {i["status"] for i in reorder["items"]} <= {"suggested", "not_required", "unknown", "rule_unavailable"}
