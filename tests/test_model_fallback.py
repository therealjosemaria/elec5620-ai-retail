"""University quota fallback is explicit, shared by capture/recommendations and cached."""
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
from openai import APIStatusError
import pytest

from backend.main import SAMPLE, create_app, fixture_extract
from backend.model_provider import ModelText


def raw_recommendation():
    return json.dumps({"recommendations": [{"product_id": "product-001", "rank": 1,
        "matches": [
            {"need_field": "taste_preferences", "need_value": "red wine", "catalogue_field": "flavour_tags", "catalogue_value": "red"},
            {"need_field": "constraints", "need_value": "no sweet drinks", "catalogue_field": "sweetness", "catalogue_value": "dry"}]}],
        "unresolved_needs": ["birthday party", "6"]})


def provider_error(status, code):
    return APIStatusError("PRIVATE_UPSTREAM_MESSAGE", response=httpx.Response(status,
        request=httpx.Request("POST", "http://fixture.invalid/v1/chat/completions")), body={"error": {"code": code}})


def test_quota_fallback_records_actual_provider_and_avoids_further_university_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    calls = []
    def complete(messages, *, provider, max_tokens):
        calls.append(provider)
        if provider == "university":
            raise provider_error(429, "quota_exceeded")
        raw = fixture_extract(SAMPLE) if "You extract customer needs" in messages[0].content else raw_recommendation()
        return ModelText(raw, provider="local", model="local-qwen")
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live", daily_limit=50)) as client:
        rid = str(uuid4())
        saved = client.post("/api/requests", json={"request_id": rid, "text": SAMPLE})
        assert saved.status_code == 201
        assert saved.json()["model_provider"] == "local" and saved.json()["fallback_reason"] == "university_quota_exhausted"
        rec = client.post(f"/api/requests/{rid}/recommendations").json()
        assert rec["model_provider"] == "local" and rec["method"] == "local_qwen_catalogue_recommendation"
        assert calls == ["university", "local", "local"]
        assert client.get("/api/status").json()["live_attempts_today"] == 1
        assert client.post(f"/api/requests/{rid}/recommendations").json()["cache_hit"] is True
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        assert calls == ["university", "local", "local"]


def test_zero_university_cap_can_use_local_without_a_university_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.delenv("ELEC5620_API_KEY", raising=False)
    calls = []
    def complete(messages, *, provider, max_tokens):
        calls.append(provider)
        assert provider == "local"
        raw = fixture_extract(SAMPLE) if "You extract customer needs" in messages[0].content else raw_recommendation()
        return ModelText(raw, provider="local", model="local-qwen")
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live", daily_limit=0)) as client:
        rid = str(uuid4())
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        assert client.post(f"/api/requests/{rid}/recommendations").json()["model_provider"] == "local"
        assert client.get("/api/status").json()["live_attempts_today"] == 0
        assert calls == ["local", "local"]


@pytest.mark.parametrize("status,code", [(429, "rate_limit_exceeded"), (401, "invalid_api_key"), (503, "upstream_unavailable")])
def test_other_provider_failures_never_silently_fall_back(tmp_path, monkeypatch, status, code):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    calls = []
    def complete(*_, provider, **kwargs):
        calls.append(provider)
        raise provider_error(status, code)
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live")) as client:
        response = client.post("/api/requests", json={"request_id": str(uuid4()), "text": SAMPLE})
        assert response.status_code == 502
        assert "PRIVATE_UPSTREAM_MESSAGE" not in response.text
        assert calls == ["university"]
