from datetime import datetime, timezone
from decimal import Decimal
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from backend.capture import CapturedEvidence, normalize
from backend.main import create_app
from backend.models import CustomerRequest, InventoryItem, Product, SalesRecord


def capture(**updates):
    return CapturedEvidence(**{
        **dict.fromkeys(["budget", "party_size", "occasion", "taste_preferences", "constraints"]),
        **updates,
    })


def test_report_field_types():
    request, missing = normalize(capture(
        budget="under $30.25", party_size="6 people",
        taste_preferences=["red wine", "dry"], constraints=["no sweet drinks"]))
    assert request.budget == Decimal("30.25")
    assert request.party_size == 6
    assert request.taste_preferences == ["red wine", "dry"]
    assert request.constraints == ["no sweet drinks"]
    assert missing == ["occasion"]
    assert request.model_dump(mode="json")["budget"] == "30.25"


@pytest.mark.parametrize("budget", ["$20 to $30", "unknown", "$1,00", "2e3"])
def test_unresolved_numeric_evidence_remains_unknown(budget):
    request, missing = normalize(capture(budget=budget))
    assert request.budget is None
    assert "budget" in missing


def test_fractional_party_size_not_rounded():
    request, missing = normalize(capture(party_size="2.5 people"))
    assert request.party_size is None
    assert "party_size" in missing


def test_each_list_item_must_be_grounded():
    evidence = capture(taste_preferences=["red", "dry"])
    with pytest.raises(ValueError):
        evidence.validate_source("red wine")
    evidence.validate_source("dry red wine")


def test_unknowns_and_independent_lists():
    first, second = CustomerRequest(), CustomerRequest()
    first.constraints.append("no sweet drinks")
    assert second.constraints == []
    request, missing = normalize(capture())
    assert request.budget is None and request.party_size is None
    assert request.taste_preferences == [] and len(missing) == 5


def test_party_size_contract_rejects_fraction_and_boolean():
    for value in (2.5, True, "six"):
        with pytest.raises(ValidationError):
            CustomerRequest(party_size=value)


def test_shared_models_keep_stock_out_of_product():
    product = Product(product_id="p1", name="Example", category="wine",
                      price=Decimal("19.95"), abv=Decimal("12"), sweetness="dry")
    item = InventoryItem(inventory_id="store1", product_id=product.product_id,
                         stock_quantity=3, reorder_threshold=5,
                         last_updated=datetime.now(timezone.utc))
    sale = SalesRecord(product_id="p1", sale_date="2026-10-20", quantity=2,
                       selling_price="19.95", cost="12.50")
    assert item.product_id == sale.product_id
    assert sale.cost == Decimal("12.50")
    with pytest.raises(ValidationError):
        Product(**product.model_dump(), stock_quantity=3)


def test_legacy_sqlite_record_is_preserved_and_normalized_without_llm(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    request_id = str(uuid4())
    evidence = capture(budget="under $30", party_size="6 people").model_dump()
    with TestClient(create_app(path, "fixture")) as client:
        with sqlite3.connect(path) as db:
            db.execute("INSERT INTO customer_requests (request_id,text,needs,missing_fields,created_at,mode) VALUES (?, ?, ?, ?, ?, ?)",
                       (request_id, "under $30 for 6 people", json.dumps(evidence), "[]",
                        datetime.now(timezone.utc).isoformat(), "live"))
        result = client.get(f"/api/requests/{request_id}").json()
        assert result["needs"]["budget"] == "30"
        assert result["evidence"] == evidence
        assert result["missing_fields"] == ["occasion", "taste_preferences", "constraints"]
        with sqlite3.connect(path) as db:
            assert json.loads(db.execute("SELECT needs FROM customer_requests").fetchone()[0]) == evidence
        assert client.get("/api/status").json()["live_attempts_today"] == 0


def test_openapi_exposes_customer_request(tmp_path):
    with TestClient(create_app(tmp_path / "db", "fixture")) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]
        assert "CustomerRequest" in schemas
        assert schemas["CustomerRequest"]["properties"]["taste_preferences"]["type"] == "array"
