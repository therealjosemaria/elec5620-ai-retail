"""University-first unlimited operation and one-shot service outage fallback."""
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
from openai import APIConnectionError, APITimeoutError, APIStatusError
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


def test_quota_fallback_records_provider_and_rechecks_primary_for_next_operation(tmp_path, monkeypatch):
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
        assert calls == ["university", "local", "university", "local"]
        assert client.get("/api/status").json()["live_attempts_today"] == 2
        assert client.post(f"/api/requests/{rid}/recommendations").json()["cache_hit"] is True
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        assert calls == ["university", "local", "university", "local"]


def test_unlimited_primary_ignores_historical_count_and_quota_latch(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    monkeypatch.setenv("LIVE_DAILY_LIMIT", "unlimited")
    calls = []
    def complete(messages, *, provider, max_tokens):
        calls.append(provider)
        assert provider == "university"
        raw = fixture_extract(SAMPLE) if "You extract customer needs" in messages[0].content else raw_recommendation()
        return ModelText(raw, provider="university", model="campus-qwen")
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live")) as client:
        from datetime import datetime, timezone
        day = datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(tmp_path / "db") as db:
            db.executemany("INSERT INTO attempts VALUES (?, 'historical', 'live', ?, 'saved')", [(str(uuid4()),day) for _ in range(60)])
            db.execute("INSERT INTO model_provider_state VALUES ('university_quota_exhausted', ?)", (day,))
        rid = str(uuid4())
        assert client.post("/api/requests", json={"request_id": rid, "text": SAMPLE}).status_code == 201
        assert client.post(f"/api/requests/{rid}/recommendations").json()["model_provider"] == "university"
        status = client.get("/api/status").json()
        assert status["live_attempts_today"] == 62 and status["local_daily_limit"] is None
        assert status["selected_provider"] == "university"
        assert calls == ["university", "university"]


@pytest.mark.parametrize("status,code", [(400, "bad_request"), (401, "invalid_api_key"), (403, "forbidden"), (404, "not_found")])
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


@pytest.mark.parametrize("failure", ["connection", "timeout", 408, 429, 500, 502, 503, 504])
def test_unavailable_primary_uses_local_once_then_recovers(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    monkeypatch.setenv("LIVE_DAILY_LIMIT", "unlimited")
    calls = []
    def complete(messages, *, provider, max_tokens):
        calls.append(provider)
        if len(calls) == 1:
            request = httpx.Request("POST", "http://fixture.invalid/v1/chat/completions")
            if failure == "connection":
                raise APIConnectionError(request=request)
            if failure == "timeout":
                raise APITimeoutError(request=request)
            raise provider_error(failure, "temporary_unavailability")
        raw = fixture_extract(SAMPLE) if "You extract customer needs" in messages[0].content else raw_recommendation()
        return ModelText(raw, provider=provider, model="local-qwen" if provider == "local" else "campus-qwen")
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live")) as client:
        rid = str(uuid4())
        saved = client.post("/api/requests", json={"request_id":rid,"text":SAMPLE})
        assert saved.status_code == 201 and saved.json()["model_provider"] == "local"
        rec = client.post(f"/api/requests/{rid}/recommendations").json()
        assert rec["model_provider"] == "university"
        assert calls == ["university", "local", "university"]
        assert client.post(f"/api/requests/{rid}/recommendations").json()["cache_hit"] is True
        assert calls == ["university", "local", "university"]


def test_invalid_output_never_falls_back_and_local_failure_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_QWEN_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-only")
    monkeypatch.setenv("LIVE_DAILY_LIMIT", "unlimited")
    calls = []
    def complete(*_, provider, **kwargs):
        calls.append(provider)
        return ModelText('{"invented":true}', provider=provider, model="campus-qwen")
    monkeypatch.setattr("backend.model_provider.complete_json", complete)
    with TestClient(create_app(tmp_path / "db", "live")) as client:
        assert client.post("/api/requests", json={"request_id":str(uuid4()),"text":SAMPLE}).status_code == 502
        assert calls == ["university"]
        calls.clear()
        def offline(*_, provider, **kwargs):
            calls.append(provider)
            raise APIConnectionError(request=httpx.Request("POST", "http://fixture.invalid"))
        monkeypatch.setattr("backend.model_provider.complete_json", offline)
        rid=str(uuid4())
        for expected in [502,409]:
            assert client.post("/api/requests", json={"request_id":rid,"text":SAMPLE}).status_code == expected
        assert calls == ["university", "local"]
