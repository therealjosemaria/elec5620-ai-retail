"""UC-M2-01 §10.3: no substitution of partial preference matches; no network."""
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from backend.main import SAMPLE, create_app
from backend.models import CustomerRequest, Product
from backend.qwen_recommendations import validate_choices
from backend.recommendations import recommend_drinks, SUITABILITY_LIMITATION


def product(pid, colour, sweetness):
    return Product(product_id=pid, name=pid, category="Wine", price="25", abv="12",
                   sweetness=sweetness, flavour_tags=[colour])


PRODUCTS = [product("dry-red", "red", "dry"), product("sweet-white", "white", "sweet")]


def choices(products=PRODUCTS):
    return json.dumps({"recommendations": [
        {"product_id": p.product_id, "rank": 1, "matches": [
            {"need_field": "taste_preferences", "need_value": "red wine" if "red" in p.flavour_tags else "sweet",
             "catalogue_field": "flavour_tags" if "red" in p.flavour_tags else "sweetness",
             "catalogue_value": "red" if "red" in p.flavour_tags else "sweet"}]} for p in products],
        "unresolved_needs": []})


@pytest.mark.parametrize("preferences", [["red wine", "sweet"], ["sweet red wine"]])
def test_fixture_requires_all_preferences_on_one_product(preferences):
    result = recommend_drinks(CustomerRequest(taste_preferences=preferences), lambda: PRODUCTS)
    assert result.outcome == "no_match" and result.recommendations == []


def test_live_rejects_separate_partial_matches_even_with_true_evidence():
    needs = CustomerRequest(taste_preferences=["red wine", "sweet"], occasion="dinner", party_size=2)
    result = validate_choices(choices(), needs, PRODUCTS)
    assert result.outcome == "no_match" and not result.recommendations
    assert SUITABILITY_LIMITATION in result.limitations
    assert any("partial matches are not offered" in line for line in result.limitations)


def test_live_keeps_a_real_combined_match_and_explains_every_preference():
    sweet_red = product("sweet-red", "red", "sweet")
    needs = CustomerRequest(taste_preferences=["red wine", "sweet"])
    result = validate_choices(choices([sweet_red]), needs, PRODUCTS + [sweet_red])
    assert [r.product.product_id for r in result.recommendations] == ["sweet-red"]
    assert result.recommendations[0].matched_needs == ["red wine", "sweet"]
    assert "sweetness: sweet" in result.recommendations[0].explanation


def test_unknown_preference_without_evidence_is_not_silently_ignored():
    needs = CustomerRequest(taste_preferences=["red wine", "a floral finish"])
    result = validate_choices(choices([PRODUCTS[0]]), needs, PRODUCTS)
    assert result.outcome == "no_match" and not result.recommendations


def test_old_cache_is_corrected_and_persisted_without_regeneration(tmp_path):
    path, calls, rid = tmp_path / "db", [], str(uuid4())
    def forbidden(*_):
        calls.append(1)
        pytest.fail("Cache migration must not call any model")
    with TestClient(create_app(path, "fixture", recommendation_generator=forbidden)) as client:
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        with sqlite3.connect(path) as db:
            needs = CustomerRequest(taste_preferences=["red wine", "sweet"], occasion="dinner", party_size=2, budget="25")
            db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?", (needs.model_dump_json(), rid))
            # Reproduce the old validator accepting an OR match from true facts.
            old = validate_choices(choices([PRODUCTS[0]]), CustomerRequest(taste_preferences=["red wine"]), PRODUCTS).model_dump(mode="json")
            old["limitations"] = ["Catalogue has no occasion or party-size suitability metadata; those needs remain unresolved.",
                                  'Catalogue evidence did not resolve the stated need: "dinner".']
            payload = dict(old, request_id=rid, mode="live", created_at="2026-10-28T08:58:23Z",
                           catalogue_digest="old-snapshot", model_provider="university", model_name="campus-qwen")
            db.execute("INSERT INTO recommendation_results VALUES (?, 'live', 'saved', ?, ?)",
                       (rid, json.dumps(payload), payload["created_at"]))
        for _ in range(2):
            saved = client.post(f"/api/requests/{rid}/recommendations").json()
            assert saved["outcome"] == "no_match" and saved["cache_hit"] is True
            assert saved["revalidated_offline"] is True and saved["model_provider"] == "university"
            assert saved["created_at"].startswith("2026-10-28T08:58:23")
            assert SUITABILITY_LIMITATION in saved["limitations"]
            assert not any('"dinner"' in line for line in saved["limitations"])
        workflow = client.post(f"/api/requests/{rid}/workflow").json()
        assert workflow["outcome"] == "no_match" and not workflow["availability"]
        assert not any(e["receiver"] == "inventory_procurement_agent" for e in workflow["trace"])
        with sqlite3.connect(path) as db:
            stored = json.loads(db.execute("SELECT payload FROM recommendation_results WHERE request_id=?", (rid,)).fetchone()[0])
            assert stored["recommendations"] == [] and stored["preference_validation_version"] == 2
        assert calls == []
