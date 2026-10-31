"""Prototype assumptions, real catalogue ABV, and no additional model calls."""
import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.models import CustomerRequest, Product
from backend.main import SAMPLE, create_app
from backend.qwen_recommendations import validate_choices
from backend.recommendations import combined_preferences, recommend_drinks
from backend.servings import MARKER, serving_note


def product(name, category, abv):
    return Product(product_id="test", name=name, category=category, price="25",
                   abv=abv, sweetness="dry", flavour_tags=[])


@pytest.mark.parametrize("name,category,abv,pours,standard", [
    ("Shiraz 750ml", "Wine", "14.5", "5 full servings", "8.6"),
    ("Moscato 750ml", "Wine", "7.5", "5 full servings", "4.4"),
    ("Pale Ale 6-pack", "Beer", "4.8", "6 full servings", "8.5"),
    ("Premium Vodka 700ml", "Spirits", "40", "23 full servings", "22.1"),
    ("Beer 330ml", "Beer", "4.8", "1 full servings", "1.2"),
])
def test_catalogue_sizes_and_abv_determine_estimates(name, category, abv, pours, standard):
    note = serving_note(product(name, category, abv))
    assert pours in note
    assert f"approximately {standard} Australian standard drinks" in note
    assert "Servings are not standard drinks" in note
    assert "per-person consumption recommendation" in note
    if name == "Pale Ale 6-pack":
        assert "6 x 375 ml" in note and "explicit prototype assumption" in note
    if category == "Spirits":
        assert "30 ml per serving" in note and "10 ml left over" in note


@pytest.mark.parametrize("name,category", [("Unknown beer", "Beer"), ("Vodka", "Spirits"),
    ("Wine 700ml or 750ml", "Wine"), ("Wine 0ml", "Wine"), ("Wine 750ml", "Unknown")])
def test_unknown_or_ambiguous_sizes_are_not_invented(name, category):
    note = serving_note(product(name, category, "12"))
    assert "unavailable" in note and "Australian standard drinks" not in note


def test_party_size_does_not_invalidate_matching_product_or_multiply_alcohol():
    p = product("Shiraz 750ml", "Wine", "14.5")
    request = CustomerRequest(taste_preferences=["wine"], party_size=12, occasion="dinner")
    result = recommend_drinks(request, lambda: [p])
    assert result.outcome == "complete"
    assert "5 full servings" in result.recommendations[0].explanation
    assert "assumes one serving per person" in " ".join(result.limitations)
    assert "one package does not cover the stated 12 people" in result.recommendations[0].explanation
    again = combined_preferences(request, result)
    assert again.model_dump() == result.model_dump()


def test_model_evidence_and_fixture_share_the_same_estimate():
    p = product("Premium Vodka 700ml", "Spirits", "40")
    request = CustomerRequest(taste_preferences=["spirits"], party_size=3)
    raw = json.dumps({"recommendations": [{"product_id": p.product_id, "rank": 1,
        "matches": [{"need_field": "taste_preferences", "need_value": "spirits",
                     "catalogue_field": "category", "catalogue_value": "Spirits"}]}],
        "unresolved_needs": ["3"]})
    live = validate_choices(raw, request, [p])
    fixture = recommend_drinks(request, lambda: [p])
    assert live.outcome == fixture.outcome == "complete"
    assert live.recommendations[0].explanation.split(MARKER)[1] == fixture.recommendations[0].explanation.split(MARKER)[1]


def test_missing_serving_metadata_keeps_valid_recommendation_and_note_is_idempotent():
    request = CustomerRequest(taste_preferences=["beer"], party_size=3)
    result = recommend_drinks(request, lambda: [product("Unknown beer", "Beer", "4.8")])
    assert result.outcome == "complete" and len(result.recommendations) == 1
    assert "unavailable" in result.recommendations[0].explanation
    assert combined_preferences(request, result).model_dump() == result.model_dump()


def test_without_party_size_no_extra_estimate_is_added():
    result = recommend_drinks(CustomerRequest(taste_preferences=["wine"]),
                              lambda: [product("Wine 750ml", "Wine", "12")])
    assert MARKER not in result.recommendations[0].explanation


def test_existing_saved_result_gains_estimate_without_another_model_attempt(tmp_path):
    path, rid, calls = tmp_path / "db", str(uuid4()), []
    def generator(request, products):
        calls.append(1)
        return json.dumps({"recommendations": [{"product_id": "product-001", "rank": 1,
            "matches": [{"need_field": "taste_preferences", "need_value": "wine",
                         "catalogue_field": "category", "catalogue_value": "Wine"}]}],
            "unresolved_needs": ["6"]})
    with TestClient(create_app(path, "fixture", recommendation_generator=generator)) as client:
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        with sqlite3.connect(path) as db:
            db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?",
                       (CustomerRequest(taste_preferences=["wine"], party_size=6).model_dump_json(), rid))
        first = client.post(f"/api/requests/{rid}/recommendations").json()
        assert len(calls) == 1
        with sqlite3.connect(path) as db:
            old = json.loads(db.execute("SELECT payload FROM recommendation_results WHERE request_id=?", (rid,)).fetchone()[0])
            old["preference_validation_version"] = 2
            old["recommendations"][0]["explanation"] = old["recommendations"][0]["explanation"].split(MARKER)[0].strip()
            db.execute("UPDATE recommendation_results SET payload=? WHERE request_id=?", (json.dumps(old), rid))
        for _ in range(2):
            updated = client.post(f"/api/requests/{rid}/recommendations").json()
            assert updated["cache_hit"] and updated["revalidated_offline"]
            assert updated["created_at"] == first["created_at"]
            assert updated["model_provider"] == first["model_provider"]
            assert updated["recommendations"][0]["explanation"].count(MARKER) == 1
            assert "5 full servings" in updated["recommendations"][0]["explanation"]
        assert len(calls) == 1


@pytest.mark.parametrize("case,party_size,outcome", [
    ("birthday", 5, "complete"),
    ("larger_group", 6, "partial"),
    ("stale", 5, "partial"),
    ("unknown_size", 5, "partial"),
    ("unsupported_combination", 5, "no_match"),
])
def test_full_customer_workflow_distinguishes_context_from_real_gaps(tmp_path, case, party_size, outcome):
    path, rid = tmp_path / "db", str(uuid4())
    with TestClient(create_app(path, "fixture")) as client:
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        needs = CustomerRequest(taste_preferences=["red wine"], occasion="22nd birthday party",
                                party_size=party_size, budget="50")
        if case == "unsupported_combination":
            needs.taste_preferences.append("sweet")
        with sqlite3.connect(path) as db:
            db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?", (needs.model_dump_json(), rid))
            if case == "stale":
                db.execute("UPDATE inventory_items SET last_updated='2020-01-01T00:00:00+00:00'")
            if case == "unknown_size":
                db.execute("UPDATE products SET name='Unknown package' WHERE category='Wine'")
            before = db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall()
        response = client.post(f"/api/requests/{rid}/workflow")
        assert response.status_code == 200
        report = response.json()
        assert report["outcome"] == outcome
        if case == "birthday":
            assert len(report["budget"]["products"]) == 2
            assert all(row["status"] == "Available" for row in report["availability"])
            assert all("one package covers the stated 5 people" in row["explanation"]
                       for row in report["recommendations"]["recommendations"])
            assert "not a verified catalogue suitability claim" in " ".join(report["limitations"])
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT * FROM inventory_items ORDER BY product_id").fetchall() == before
