"""UC-M1-02 acceptance: §6.1.2 and §10.2, including unchanged source values."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from time import perf_counter

from fastapi.testclient import TestClient
import pytest

from backend.main import create_app
from backend.retail_data import ensure_retail_data
from backend.stock import (InventoryLookupRequest, InventoryProcurementAgent,
                           LookupStatus, Requester, ensure_inventory_data)

NOW = datetime(2026, 10, 28, 3, tzinfo=timezone.utc)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "inventory.sqlite3"
    with sqlite3.connect(path) as db:
        ensure_retail_data(db)
        ensure_inventory_data(db, now=NOW)
    return path


def agent(path, **kwargs):
    return InventoryProcurementAgent(path, requester=Requester.FOUNDER_OPERATOR,
        authorise=lambda _: True, clock=lambda: NOW, **kwargs)


def batch(service, ids):
    return service.lookup_stock(InventoryLookupRequest(
        product_ids=ids, requester=Requester.FOUNDER_OPERATOR))


def snapshot(path):
    with sqlite3.connect(path) as db:
        return list(db.iterdump())


def test_exact_values_read_only_dedup_and_zero_stock(source):
    before = snapshot(source)
    result = batch(agent(source), ["product-001", "product-004", "product-001"])
    assert [r.product_id for r in result] == ["product-001", "product-004"]
    assert all(r.status == LookupStatus.FOUND for r in result)
    assert result[0].item.stock_quantity == 24
    assert result[0].item.reorder_threshold == 10
    assert result[0].item.last_updated == NOW
    assert result[1].item.stock_quantity == 0  # no availability decision in lookup
    assert snapshot(source) == before


def test_invalid_unknown_stale_continue_with_valid_ids(source):
    results = batch(agent(source), [" ", "bad/id", "unknown", "product-005", "product-001"])
    assert [r.status for r in results] == [LookupStatus.ERROR, LookupStatus.ERROR,
        LookupStatus.NOT_FOUND, LookupStatus.STALE, LookupStatus.FOUND]
    assert all(r.item is None for r in results[:3])
    assert results[3].item.stock_quantity == 12
    assert results[3].item.last_updated == NOW - timedelta(days=3)


@pytest.mark.parametrize("column,value", [
    ("stock_quantity", None), ("last_updated", None), ("reorder_threshold", None),
    ("stock_quantity", -1), ("reorder_threshold", -1), ("last_updated", "not-a-date"),
    ("last_updated", "2026-10-28T03:00:00"), ("last_updated", "2026-10-29T03:00:00Z"),
])
def test_incomplete_or_conflicting_record_is_error(source, column, value):
    with sqlite3.connect(source) as db:
        db.execute(f"UPDATE inventory_items SET {column}=? WHERE product_id='product-001'", (value,))
    result = batch(agent(source), ["product-001", "product-002"])
    assert result[0].status == LookupStatus.ERROR and result[0].item is None
    assert result[1].status == LookupStatus.FOUND


def test_freshness_boundary_and_success_only_consumer(source):
    with sqlite3.connect(source) as db:
        db.execute("UPDATE inventory_items SET last_updated=? WHERE product_id='product-001'",
                   ((NOW - timedelta(hours=24)).isoformat(),))
    assert batch(agent(source), ["product-001"])[0].status == LookupStatus.FOUND
    assert agent(source).lookup_stock("product-001").stock_quantity == 24
    with pytest.raises(LookupError):
        agent(source).lookup_stock("product-005")
    assert batch(agent(source, max_age=timedelta(hours=23)), ["product-001"])[0].status == LookupStatus.STALE


def test_authorisation_checked_before_opening_source(tmp_path):
    missing = tmp_path / "never-created.sqlite3"
    service = InventoryProcurementAgent(missing, requester=Requester.FOUNDER_OPERATOR,
                                       authorise=lambda _: False)
    with pytest.raises(PermissionError):
        batch(service, ["product-001"])
    request = InventoryLookupRequest(product_ids=["product-001"], requester=Requester.CUSTOMER_AGENT)
    with pytest.raises(PermissionError):
        agent(missing).lookup_stock(request)
    assert not missing.exists()


def test_source_outage_does_not_create_database(tmp_path):
    path = tmp_path / "missing.sqlite3"
    results = batch(agent(path), ["product-001", "product-002"])
    assert all(r.status == LookupStatus.ERROR and r.item is None for r in results)
    assert not path.exists()


def test_empty_selection_and_invalid_config_do_not_query(tmp_path):
    with pytest.raises(ValueError):
        InventoryLookupRequest(product_ids=[], requester=Requester.FOUNDER_OPERATOR)
    with pytest.raises(ValueError):
        agent(tmp_path / "missing", max_age=timedelta(0))


def test_seed_preserves_existing_source_and_single_store(source):
    before = snapshot(source)
    with sqlite3.connect(source) as db:
        ensure_inventory_data(db, now=NOW + timedelta(days=10))
        assert db.execute("SELECT count(*) FROM inventory").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO inventory VALUES (2, 'another', 'Another')")
    assert snapshot(source) == before


def test_api_authorisation_selection_read_only_and_no_model(source):
    def forbidden_model(_):
        pytest.fail("Stock lookup must never call the model")
    # API uses the real clock; keep this fixture independent of the host's date.
    with sqlite3.connect(source) as db:
        db.execute("UPDATE inventory_items SET last_updated=? WHERE product_id='product-001'",
                   (datetime.now(timezone.utc).isoformat(),))
    with TestClient(create_app(source, "fixture", extractor=forbidden_model,
                              operator_token="test-operator")) as client:
        before = snapshot(source)
        assert client.post("/api/inventory/lookup", json={"product_ids": ["product-001"]}).status_code == 403
        assert client.post("/api/inventory/lookup", json={"product_ids": ["product-001"]},
                           headers={"Authorization": "Bearer wrong"}).status_code == 403
        headers = {"Authorization": "Bearer test-operator"}
        assert client.post("/api/inventory/lookup", json={"product_ids": []}, headers=headers).status_code == 400
        assert client.post("/api/inventory/lookup", json={"product_ids": ["product-001"],
                           "requester": "founder_operator"}, headers=headers).status_code == 422
        response = client.post("/api/inventory/lookup", json={"product_ids": ["product-001", "unknown"]}, headers=headers)
        assert response.status_code == 200
        assert response.json()[0]["item"]["stock_quantity"] == 24
        assert response.json()[1]["status"] == "not_found"
        assert snapshot(source) == before


def test_unconfigured_operator_token_denies_by_default(source):
    with TestClient(create_app(source, "fixture", operator_token="")) as client:
        assert client.post("/api/inventory/lookup", json={"product_ids": ["product-001"]},
                           headers={"Authorization": "Bearer anything"}).status_code == 403


def test_standard_batch_under_two_seconds(source):
    durations = []
    for _ in range(20):
        start = perf_counter()
        result = batch(agent(source), [f"product-{i:03d}" for i in range(1, 7)])
        durations.append(perf_counter() - start)
        assert len(result) == 6
    assert sorted(durations)[18] < 2
