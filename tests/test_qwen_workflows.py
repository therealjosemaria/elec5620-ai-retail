"""Qwen boundary, at-most-once storage, quotas and real LangGraph handoffs; no network."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from backend.main import SAMPLE, create_app, fixture_extract
from backend.models import CustomerRequest
from backend.qwen_recommendations import live_recommend, validate_choices
from backend.retail_data import load_products


def choices():
    return {"recommendations": [
        {"product_id": pid, "rank": rank, "matches": [
            {"need_field": "taste_preferences", "need_value": "red wine", "catalogue_field": "flavour_tags", "catalogue_value": "red"},
            {"need_field": "constraints", "need_value": "no sweet drinks", "catalogue_field": "sweetness", "catalogue_value": "dry"},
        ]} for pid, rank in [("product-001", 1), ("product-002", 2)]],
        "unresolved_needs": ["birthday party", "6"]}


def captured(client, text=SAMPLE):
    rid = str(uuid4())
    response = client.post("/api/requests", json={"request_id": rid, "text": text})
    assert response.status_code == 201
    return rid


@pytest.fixture
def system(tmp_path):
    path, calls = tmp_path / "db", []
    def generate(needs, products):
        calls.append((needs, products))
        return json.dumps(choices())
    app = create_app(path, "fixture", recommendation_generator=generate, operator_token="test-operator")
    with TestClient(app) as client:
        yield client, path, calls


def test_generation_saved_and_reused_by_every_read_and_workflow(system):
    client, path, calls = system
    rid = captured(client)
    for suffix in ("recommendations", "budget-filter", "availability"):
        assert client.get(f"/api/requests/{rid}/{suffix}").status_code == 409
    assert calls == []
    first = client.post(f"/api/requests/{rid}/recommendations")
    assert first.status_code == 200 and first.json()["method"] == "campus_qwen_catalogue_recommendation"
    assert first.json()["cache_hit"] is False
    for _ in range(3):
        cached = client.post(f"/api/requests/{rid}/recommendations").json()
        assert cached["cache_hit"] is True
        assert cached["created_at"] == first.json()["created_at"]
        assert client.get(f"/api/requests/{rid}/recommendations").json()["cache_hit"] is True
        assert client.get(f"/api/requests/{rid}/budget-filter").status_code == 200
        assert client.get(f"/api/requests/{rid}/availability?within_budget=true").status_code == 200
    report = client.post(f"/api/requests/{rid}/workflow").json()
    assert report["recommendations"]["cache_hit"] is True
    assert report["budget"]["products"][0]["product_id"] == "product-001"
    assert report["availability"][0]["status"] == "Available"
    edges = [(s["sender"], s["receiver"]) for s in report["trace"]]
    assert ("customer_agent", "inventory_procurement_agent") in edges
    assert ("inventory_procurement_agent", "customer_agent") in edges
    assert client.get(f"/api/workflows/{report['workflow_id']}").json() == report
    assert client.get(f"/api/requests/{rid}/workflow").json() == report
    assert len(calls) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status FROM recommendation_results WHERE request_id=?", (rid,)).fetchone()[0] == "saved"


def test_cache_survives_app_restart(system):
    client, path, calls = system
    rid = captured(client)
    assert client.post(f"/api/requests/{rid}/recommendations").status_code == 200
    def forbidden(*_):
        pytest.fail("Restart must not repeat a model call")
    with TestClient(create_app(path, "fixture", recommendation_generator=forbidden)) as restarted:
        assert restarted.post(f"/api/requests/{rid}/recommendations").json()["cache_hit"] is True
    assert len(calls) == 1


def test_concurrent_generation_is_reserved_once(tmp_path):
    entered, release, calls = Event(), Event(), []
    def generate(*_):
        calls.append(1); entered.set()
        assert release.wait(5)
        return json.dumps(choices())
    with TestClient(create_app(tmp_path / "db", "fixture", recommendation_generator=generate)) as client:
        rid = captured(client)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(client.post, f"/api/requests/{rid}/recommendations")
            assert entered.wait(3)
            try:
                assert client.post(f"/api/requests/{rid}/recommendations").status_code == 409
            finally:
                release.set()
            assert first.result(timeout=5).status_code == 200
        assert calls == [1]


@pytest.mark.parametrize("failure", ["provider", "invalid_json", "invented_product"])
def test_failed_generation_is_terminal_and_sanitized(tmp_path, failure, caplog):
    calls = []
    def generate(*_):
        calls.append(1)
        if failure == "provider":
            raise RuntimeError("PRIVATE_PROVIDER_SECRET")
        if failure == "invalid_json":
            return "PRIVATE_PROVIDER_SECRET"
        raw = choices(); raw["recommendations"][0]["product_id"] = "invented"
        return json.dumps(raw)
    path = tmp_path / "db"
    with TestClient(create_app(path, "live", extractor=lambda _: fixture_extract(SAMPLE),
                              recommendation_generator=generate, daily_limit=10)) as client:
        rid = captured(client)
        response = client.post(f"/api/requests/{rid}/recommendations")
        assert response.status_code == 502 and "PRIVATE_PROVIDER_SECRET" not in response.text
        assert client.post(f"/api/requests/{rid}/recommendations").status_code == 409
        report = client.post(f"/api/requests/{rid}/workflow").json()
        assert report["outcome"] == "blocked" and not report["availability"]
        assert client.get("/api/status").json()["live_attempts_today"] == 2
        assert calls == [1] and "PRIVATE_PROVIDER_SECRET" not in caplog.text
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status,payload FROM recommendation_results WHERE request_id=?", (rid,)).fetchone() == ("failed", None)


def test_capture_and_recommendations_share_daily_cap(tmp_path):
    path, calls = tmp_path / "db", []
    def generate(*_):
        calls.append(1); return json.dumps(choices())
    with TestClient(create_app(path, "live", extractor=lambda _: fixture_extract(SAMPLE),
                              recommendation_generator=generate, daily_limit=1)) as client:
        rid = captured(client)
        assert client.post(f"/api/requests/{rid}/recommendations").status_code == 429
        assert calls == []
    with TestClient(create_app(path, "live", recommendation_generator=generate, daily_limit=2)) as client:
        assert client.post(f"/api/requests/{rid}/recommendations").status_code == 200
        assert client.get("/api/status").json()["live_attempts_today"] == 2
        assert client.post(f"/api/requests/{rid}/recommendations").status_code == 200
        assert calls == [1]


def test_budget_uses_current_prices_without_regenerating_ranks(system):
    client, path, calls = system
    rid = captured(client)
    original = client.post(f"/api/requests/{rid}/recommendations").json()
    with sqlite3.connect(path) as db:
        db.execute("UPDATE products SET price='99.00' WHERE product_id='product-001'")
    filtered = client.get(f"/api/requests/{rid}/budget-filter").json()
    assert filtered["status"] == "NoMatch"
    assert client.get(f"/api/requests/{rid}/recommendations").json()["recommendations"] == original["recommendations"]
    assert len(calls) == 1


@pytest.mark.parametrize("defect", ["id", "fact", "need", "duplicate", "rank", "extra"])
def test_qwen_evidence_is_validated_against_catalogue_and_request(system, defect):
    _, path, _ = system
    with sqlite3.connect(path) as db:
        products = load_products(db)
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["no sweet drinks"], occasion="birthday party", party_size=6)
    raw = choices()
    item = raw["recommendations"][0]
    if defect == "id": item["product_id"] = "imaginary"
    if defect == "fact": item["matches"][0]["catalogue_value"] = "imaginary"
    if defect == "need": item["matches"][0]["need_value"] = "imaginary"
    if defect == "duplicate": raw["recommendations"][1]["product_id"] = item["product_id"]
    if defect == "rank": item["rank"] = "1"
    if defect == "extra": item["price"] = "1.00"
    with pytest.raises(ValueError):
        validate_choices(json.dumps(raw), needs, products)


def test_unstated_uncertainty_is_withheld_without_dropping_grounded_products(system):
    _, path, _ = system
    with sqlite3.connect(path) as db: products = load_products(db)
    needs = CustomerRequest(taste_preferences=["red wine"], constraints=["no sweet drinks"], occasion="birthday party", party_size=6)
    raw = choices(); raw["unresolved_needs"] = ["UNSTATED_MODEL_REFERENCE"]
    result = validate_choices(json.dumps(raw), needs, products)
    assert result.outcome == "complete" and len(result.recommendations) == 2
    assert "UNSTATED_MODEL_REFERENCE" not in result.model_dump_json()
    assert any("was not used" in value for value in result.limitations)


def test_qwen_handles_a_phrase_outside_the_fixture_vocabulary(system):
    _, path, _ = system
    with sqlite3.connect(path) as db:
        products = load_products(db)
    needs = CustomerRequest(taste_preferences=["a lighter red for slow sipping"])
    raw = {"recommendations": [{"product_id": "product-002", "rank": 1, "matches": [{
        "need_field": "taste_preferences", "need_value": needs.taste_preferences[0],
        "catalogue_field": "abv", "catalogue_value": "13.0"}]}], "unresolved_needs": []}
    result = validate_choices(json.dumps(raw), needs, products)
    assert result.recommendations[0].product.product_id == "product-002"
    assert result.method == "campus_qwen_catalogue_recommendation"


@pytest.mark.parametrize("provider_status", [200, 429])
def test_real_sdk_recommendation_wire_omits_budget_stock_and_price(system, monkeypatch, provider_status):
    import httpx
    import langchain_openai
    _, path, _ = system
    with sqlite3.connect(path) as db:
        products = load_products(db)
    needs = CustomerRequest(budget="30", taste_preferences=["red wine"], constraints=["no sweet drinks"], occasion="birthday party", party_size=6)
    original, calls = langchain_openai.ChatOpenAI, []
    def handler(request):
        payload = json.loads(request.content); calls.append(payload)
        assert payload["model"] == "campus-qwen" and payload["response_format"] == {"type": "json_object"}
        assert payload["max_tokens"] == 4096 and "max_completion_tokens" not in payload
        assert payload["reasoning_effort"] == "none"
        data = json.loads(payload["messages"][-1]["content"])
        assert "budget" not in data["needs"]
        assert all("price" not in p and "stock_quantity" not in p for p in data["catalogue"])
        if provider_status == 429:
            return httpx.Response(429, json={"error": {"message": "fixture quota", "type": "rate_limit"}})
        return httpx.Response(200, json={"id":"fixture", "object":"chat.completion", "created":1, "model":"campus-qwen",
            "choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":json.dumps(choices())}}]})
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    monkeypatch.setenv("ELEC5620_BASE_URL", "http://proxy.test/v1")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(langchain_openai, "ChatOpenAI", lambda **kw: original(**kw, http_client=client))
        if provider_status == 200:
            result = validate_choices(live_recommend(needs, products), needs, products)
            assert len(result.recommendations) == 2
        else:
            with pytest.raises(Exception):
                live_recommend(needs, products)
    assert len(calls) == 1


def test_known_constraint_evidence_is_completed_from_validated_facts(system):
    _, path, _ = system
    with sqlite3.connect(path) as db:
        products = load_products(db)
    raw = choices()
    raw["recommendations"][0]["matches"] = raw["recommendations"][0]["matches"][:1]
    request = CustomerRequest(taste_preferences=["red wine"], constraints=["no sweet drinks"], occasion="birthday party", party_size=6)
    result = validate_choices(json.dumps(raw), request, products)
    assert "no sweet drinks" in result.recommendations[0].matched_needs
    assert "sweetness: dry" in result.recommendations[0].explanation


def test_unknown_constraint_without_model_evidence_is_rejected(system):
    _, path, _ = system
    with sqlite3.connect(path) as db:
        products = load_products(db)
    raw = choices()
    request = CustomerRequest(taste_preferences=["red wine"], constraints=["no sweet drinks", "certified organic"], occasion="birthday party", party_size=6)
    with pytest.raises(ValueError, match="constraint"):
        validate_choices(json.dumps(raw), request, products)


def test_terminal_pending_marker_survives_restart_without_a_call(system):
    client, path, calls = system
    rid = captured(client)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO recommendation_results VALUES (?, 'live', 'pending', NULL, '2026-10-28T00:00:00Z')", (rid,))
    with TestClient(create_app(path, "fixture", recommendation_generator=lambda *_: pytest.fail("pending reservation repeated"))) as restarted:
        assert restarted.post(f"/api/requests/{rid}/recommendations").status_code == 409
    assert calls == []


def test_no_match_result_is_saved_without_repeat_generation(system):
    client, path, calls = system
    rid = captured(client)
    generated = []
    def no_match(*_):
        generated.append(1)
        return json.dumps({"recommendations": [], "unresolved_needs": ["red wine"]})
    with TestClient(create_app(path, "fixture", recommendation_generator=no_match)) as app:
        assert app.post(f"/api/requests/{rid}/recommendations").json()["outcome"] == "no_match"
        report = app.post(f"/api/requests/{rid}/workflow").json()
        assert report["outcome"] == "no_match"
        assert not any(step["receiver"] == "inventory_procurement_agent" for step in report["trace"])
        assert generated == [1] and calls == []


def test_business_graphs_have_real_inventory_handoffs_and_protected_saved_traces(system):
    client, _, calls = system
    headers = {"Authorization": "Bearer test-operator"}
    restock = client.post("/api/restocking-priorities", json={"product_id": "product-003"}, headers=headers).json()
    edges = [(e["sender"],e["receiver"]) for e in restock["trace"]]
    assert ("business_insights_agent", "inventory_procurement_agent") in edges
    assert ("inventory_procurement_agent", "business_insights_agent") in edges
    assert client.get(f"/api/workflows/{restock['workflow_id']}").status_code == 403
    assert client.get(f"/api/workflows/{restock['workflow_id']}", headers=headers).status_code == 200
    profit = client.post("/api/profit-margins", json={"product_id": "product-001"}, headers=headers).json()
    assert all(e["sender"] != "inventory_procurement_agent" and e["receiver"] != "inventory_procurement_agent" for e in profit["trace"])
    assert calls == []


def test_explicit_offline_revalidation_reuses_retained_output(system, monkeypatch):
    import backend.recommendation_store as storage
    client, path, calls = system
    rid = captured(client)
    validator = storage.validate_choices
    def rejected(*_):
        raise storage.GroundingError("Synthetic validator failure.")
    monkeypatch.setattr(storage, "validate_choices", rejected)
    assert client.post(f"/api/requests/{rid}/recommendations").status_code == 502
    assert client.post(f"/api/requests/{rid}/recommendations").status_code == 409
    monkeypatch.setattr(storage, "validate_choices", validator)
    store = storage.RecommendationStore(lambda: sqlite3.connect(path), mode="offline", daily_limit=0)
    result = store.revalidate(rid)
    assert result.revalidated_offline is True
    assert result.recommendations[0].product.product_id == "product-001"
    assert client.get(f"/api/requests/{rid}/recommendations").json()["revalidated_offline"] is True
    assert len(calls) == 1
    with pytest.raises(storage.RecommendationError):
        store.revalidate(rid)


def test_offline_revalidation_rejects_missing_output_and_changed_needs(system, monkeypatch):
    import backend.recommendation_store as storage
    client, path, calls = system
    rid = captured(client)
    store = storage.RecommendationStore(lambda: sqlite3.connect(path), mode="offline", daily_limit=0)
    with pytest.raises(storage.RecommendationError):
        store.revalidate(rid)
    def rejected(*_):
        raise storage.GroundingError("Synthetic validator failure.")
    monkeypatch.setattr(storage, "validate_choices", rejected)
    assert client.post(f"/api/requests/{rid}/recommendations").status_code == 502
    with sqlite3.connect(path) as db:
        needs = json.loads(db.execute("SELECT payload FROM request_inbox WHERE request_id=?", (rid,)).fetchone()[0])
        needs["occasion"] = "changed"
        db.execute("UPDATE request_inbox SET payload=? WHERE request_id=?", (json.dumps(needs),rid))
    with pytest.raises(storage.RecommendationError, match="needs changed"):
        store.revalidate(rid)
    assert len(calls) == 1
