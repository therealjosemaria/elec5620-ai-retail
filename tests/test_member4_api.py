from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.main import create_app


def product_payload(
    product_id: str,
    price: str,
) -> dict:
    return {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "category": "Wine",
        "price": price,
        "abv": "13.5",
        "sweetness": "Dry",
        "flavour_tags": ["fruit"],
    }


def test_budget_filter_api_retains_affordable_products(tmp_path):
    app = create_app(
        db_path=tmp_path / "test.sqlite3",
        mode="fixture",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/member4/budget-filter",
            json={
                "request": {
                    "budget": "30.00",
                },
                "candidates": [
                    product_payload("WINE-001", "25.00"),
                    product_payload("WINE-002", "35.00"),
                ],
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["budget"] == "30.00"
    assert body["status"] == "Matched"
    assert [
        item["product_id"]
        for item in body["products"]
    ] == ["WINE-001"]
    assert body["excluded_product_ids"] == ["WINE-002"]


def test_budget_filter_api_rejects_missing_budget(tmp_path):
    app = create_app(
        db_path=tmp_path / "test.sqlite3",
        mode="fixture",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/member4/budget-filter",
            json={
                "request": {},
                "candidates": [
                    product_payload("WINE-001", "25.00"),
                ],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Customer budget is missing."
    )


def test_availability_api_classifies_products(tmp_path):
    app = create_app(
        db_path=tmp_path / "test.sqlite3",
        mode="fixture",
    )
    timestamp = datetime.now(timezone.utc).isoformat()

    with TestClient(app) as client:
        response = client.post(
            "/api/member4/availability-check",
            json={
                "requester_role": "CustomerAgent",
                "lookups": [
                    {
                        "product_id": "WINE-001",
                        "stock_quantity": 5,
                        "last_updated": timestamp,
                        "status": "Found",
                    },
                    {
                        "product_id": "WINE-002",
                        "stock_quantity": 0,
                        "last_updated": timestamp,
                        "status": "Found",
                    },
                    {
                        "product_id": "WINE-404",
                        "status": "NotFound",
                        "limitation": "Product was not found.",
                    },
                    {
                        "product_id": "WINE-003",
                        "stock_quantity": 2,
                        "last_updated": timestamp,
                        "status": "Stale",
                        "limitation": "Inventory record is stale.",
                    },
                ],
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body[0]["status"] == "Available"
    assert body[1]["status"] == "Unavailable"
    assert body[2]["status"] == "Unknown"
    assert body[3]["status"] == "Unknown"


def test_availability_api_rejects_unknown_role(tmp_path):
    app = create_app(
        db_path=tmp_path / "test.sqlite3",
        mode="fixture",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/member4/availability-check",
            json={
                "requester_role": "UnauthorisedUser",
                "lookups": [],
            },
        )

    assert response.status_code == 422