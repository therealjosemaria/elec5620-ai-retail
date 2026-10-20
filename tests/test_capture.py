import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from backend.main import SAMPLE, create_app


def submit(client, text=SAMPLE, request_id=None):
    return client.post("/api/requests", json={"request_id": request_id or str(uuid4()), "text": text})


def empty_needs(**updates):
    return json.dumps({
        **dict.fromkeys(["budget", "party_size", "occasion", "taste_preferences", "constraints"]),
        **updates,
    })


def test_fixture_roundtrip_and_restart(tmp_path):
    path = tmp_path / "test.sqlite3"
    with TestClient(create_app(path, "fixture")) as client:
        result = submit(client)
        assert result.status_code == 201
        record = result.json()
        assert record["needs"]["budget"] == "30"
        assert record["needs"]["party_size"] == 6
        assert record["needs"]["taste_preferences"] == ["red wine"]
        assert record["needs"]["status"] == "RequestConfirmed"
        assert record["evidence"]["budget"] == "under $30"
        assert record["missing_fields"] == []
        assert client.get(f'/api/requests/{record["request_id"]}').json() == record
        assert client.get("/api/status").json()["live_attempts_today"] == 0
    with TestClient(create_app(path, "fixture")) as client:
        assert client.get(f'/api/requests/{record["request_id"]}').json() == record
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM customer_requests").fetchone()[0] == 1


def test_missing_fields(tmp_path):
    with TestClient(create_app(tmp_path / "db", "fixture",
                              extractor=lambda _: empty_needs(taste_preferences="red wine"))) as client:
        response = submit(client, "red wine")
        assert response.status_code == 201
        assert response.json()["needs"]["budget"] is None
        assert response.json()["missing_fields"] == ["budget", "party_size", "occasion", "constraints"]


@pytest.mark.parametrize("text", ["", "   ", "x" * 1501])
def test_invalid_input_never_calls_model(tmp_path, text):
    calls = []
    with TestClient(create_app(tmp_path / "db", "live", extractor=lambda _: calls.append(1))) as client:
        assert submit(client, text).status_code == 422
        assert calls == []


@pytest.mark.parametrize("output", [
    "not JSON", '{"budget":null}', empty_needs(budget="$999"),
    empty_needs(party_size=6), empty_needs(extra_field="invented"),
    empty_needs(budget=""),
])
def test_bad_output_not_saved(tmp_path, output):
    path = tmp_path / "db"
    with TestClient(create_app(path, "live", extractor=lambda _: output)) as client:
        assert submit(client).status_code == 502
        assert client.get("/api/status").json()["live_attempts_today"] == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM customer_requests").fetchone()[0] == 0


def test_duplicate_and_conflicting_ids(tmp_path):
    calls = []
    def extract(_):
        calls.append(1)
        return empty_needs()
    with TestClient(create_app(tmp_path / "db", "live", extractor=extract)) as client:
        request_id = str(uuid4())
        first = submit(client, request_id=request_id)
        assert submit(client, request_id=request_id).json() == first.json()
        assert submit(client, "different text", request_id).status_code == 409
        assert len(calls) == 1


@pytest.mark.parametrize("http_status", [200, 429])
def test_real_sdk_wire_format_and_no_retries(monkeypatch, http_status):
    """Exercise the installed provider SDK using intercepted HTTP, not the university."""
    import httpx
    import langchain_openai
    from backend.main import live_extract
    original = langchain_openai.ChatOpenAI
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.url.path == "/v1/chat/completions"
        assert payload["model"] == "campus-qwen"
        assert payload.get("max_completion_tokens", payload.get("max_tokens")) == 2048
        if http_status == 429:
            return httpx.Response(429, json={"error": {"message": "test quota", "type": "rate_limit"}})
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 1, "model": "campus-qwen",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": empty_needs()},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    monkeypatch.setenv("ELEC5620_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("ELEC5620_BASE_URL", "http://proxy.test/v1")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(langchain_openai, "ChatOpenAI",
                            lambda **kwargs: original(**kwargs, http_client=client))
        if http_status == 200:
            assert live_extract(SAMPLE) == empty_needs()
        else:
            with pytest.raises(Exception):
                live_extract(SAMPLE)
        assert len(calls) == 1


def test_local_cap_survives_restart(tmp_path):
    path = tmp_path / "db"
    for expected in [201, 429]:
        with TestClient(create_app(path, "live", extractor=lambda _: empty_needs(), daily_limit=1)) as client:
            assert submit(client).status_code == expected
            assert client.get("/api/status").json()["live_attempts_today"] == 1


def test_failed_attempt_is_not_retried_or_leaked(tmp_path):
    calls = []
    def broken(_):
        calls.append(1)
        raise RuntimeError("private-provider-secret")
    with TestClient(create_app(tmp_path / "db", "live", extractor=broken)) as client:
        request_id = str(uuid4())
        result = submit(client, request_id=request_id)
        assert result.status_code == 502
        assert "private-provider-secret" not in result.text
        assert submit(client, request_id=request_id).status_code == 409
        assert len(calls) == 1


def test_missing_key_does_not_spend_budget(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEC5620_API_KEY", raising=False)
    with TestClient(create_app(tmp_path / "db", "live")) as client:
        assert submit(client).status_code == 503
        assert client.get("/api/status").json()["live_attempts_today"] == 0


def test_fixture_rejects_arbitrary_text(tmp_path):
    with TestClient(create_app(tmp_path / "db", "fixture")) as client:
        assert submit(client, "anything else").status_code == 422
        assert client.get(f"/api/requests/{uuid4()}").status_code == 404


def test_parallel_duplicate_spends_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    started, finish = Event(), Event()
    calls = []
    def slow(_):
        calls.append(1)
        started.set()
        assert finish.wait(5)
        return empty_needs()
    with TestClient(create_app(tmp_path / "db", "live", extractor=slow)) as client:
        request_id = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(submit, client, SAMPLE, request_id)
            try:
                assert started.wait(5)
                assert submit(client, request_id=request_id).status_code == 409
            finally:
                finish.set()
            assert future.result().status_code == 201
        assert len(calls) == 1
