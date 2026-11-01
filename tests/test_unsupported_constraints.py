"""Missing hard-constraint evidence is a domain outcome, not a provider outage."""
import json
import sqlite3
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest

from backend.main import SAMPLE, create_app
from backend.models import CustomerRequest, Product
from backend.qwen_recommendations import GroundingError, validate_choices
from backend.recommendation_store import RecommendationStore


PRODUCTS = [Product(product_id="product-001", name="Shiraz 750ml", category="Wine",
                    price="25", abv="14.5", sweetness="dry", flavour_tags=["red"])]


def raw(*, unresolved=None, fact="red"):
    return json.dumps({"recommendations": [{"product_id": "product-001", "rank": 1,
        "matches": [{"need_field": "taste_preferences", "need_value": "red wine",
                     "catalogue_field": "flavour_tags", "catalogue_value": fact}]}],
        "unresolved_needs": unresolved or []})


@pytest.mark.parametrize("constraint", ["No merlot wine", "certified organic", "no sulphites"])
def test_unverified_constraint_is_explained_without_inventing_compliance(constraint):
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=[constraint])
    result = validate_choices(raw(), needs, PRODUCTS)
    assert result.outcome == "unsupported_request" and result.recommendations == []
    assert any(f'cannot verify your constraint "{constraint}"' in line for line in result.limitations)
    assert any("has not been ignored" in line for line in result.limitations)


def test_empty_model_result_with_explicit_unresolved_constraint_is_clarification():
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["No merlot wine"])
    result = validate_choices(json.dumps({"recommendations": [], "unresolved_needs": ["No merlot wine"]}), needs, PRODUCTS)
    assert result.outcome == "unsupported_request" and not result.recommendations


def test_supported_exclusion_is_completed_from_catalogue_facts():
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["no sweet drinks"])
    result = validate_choices(raw(), needs, PRODUCTS)
    assert result.outcome == "complete"
    assert "no sweet drinks" in result.recommendations[0].matched_needs


def test_invented_fact_still_raises_even_with_an_unsupported_constraint():
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["No merlot wine"])
    with pytest.raises(GroundingError, match="invented product fact"):
        validate_choices(raw(fact="invented"), needs, PRODUCTS)


def test_contradictory_known_constraint_is_not_softened_to_clarification():
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["sweet", "No merlot wine"])
    with pytest.raises(GroundingError, match="contradicts"):
        validate_choices(raw(), needs, PRODUCTS)


def test_api_saves_and_reuses_clarification_and_skips_budget_and_stock(tmp_path):
    path, rid, calls = tmp_path / "db", str(uuid4()), []
    def generator(*_):
        calls.append(1)
        return raw(unresolved=["occasion: engagement party", "party_size: 5"])
    with TestClient(create_app(path, "fixture", recommendation_generator=generator)) as client:
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        needs = CustomerRequest(taste_preferences=["red wine"], constraints=["No merlot wine"],
                                party_size=5, budget="100", occasion="engagement party")
        with sqlite3.connect(path) as db:
            db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?", (needs.model_dump_json(), rid))
            before = db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall()
        for _ in range(2):
            response = client.post(f"/api/requests/{rid}/workflow")
            assert response.status_code == 200
            report = response.json()
            assert report["outcome"] == "needs_clarification"
            assert report["budget"] is None and report["availability"] == []
            assert report["recommendations"]["outcome"] == "unsupported_request"
            assert any('"No merlot wine"' in line for line in report["limitations"])
            assert not any(event["receiver"] == "inventory_procurement_agent" for event in report["trace"])
        assert len(calls) == 1
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT status FROM recommendation_results WHERE request_id=?", (rid,)).fetchone()[0] == "saved"
            assert before == db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall()
            # Reproduce the older validator's terminal failure with retained output.
            db.execute("UPDATE recommendation_results SET status='failed',payload=NULL WHERE request_id=?", (rid,))
        restored = RecommendationStore(lambda: sqlite3.connect(path), mode="offline", daily_limit=0).revalidate(UUID(rid))
        assert restored.outcome == "unsupported_request" and restored.revalidated_offline
        assert len(calls) == 1


def test_fixture_unsupported_requirement_uses_same_non_error_workflow(tmp_path):
    path, rid = tmp_path / "db", str(uuid4())
    with TestClient(create_app(path, "fixture")) as client:
        client.post("/api/requests", json={"request_id": rid, "text": SAMPLE})
        with sqlite3.connect(path) as db:
            needs = CustomerRequest(taste_preferences=["red wine"], constraints=["No merlot wine"])
            db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?", (needs.model_dump_json(), rid))
        response = client.post(f"/api/requests/{rid}/workflow")
        assert response.status_code == 200 and response.json()["outcome"] == "needs_clarification"
