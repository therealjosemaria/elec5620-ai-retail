"""Traceable acceptance cases for report §10.1 and Figures 8/13/18."""
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from backend.capture import CapturedEvidence, normalize
from backend.handoff import RequestConsumer, read_published_request
from backend.main import create_app


def evidence(**values):
    return dict(budget=None, party_size=None, occasion=None,
                taste_preferences=[], constraints=[]) | values


def send(client, text, request_id=None):
    return client.post("/api/requests", json={"request_id": request_id or str(uuid4()), "text": text})


@pytest.mark.parametrize("phrase,expected", [
    ("fifty dollars", "50"), ("one hundred and twenty-five dollars", "125"),
    ("$1,250.50", "1250.50"), ("2k", "2000"), ("twenty point five", "20.5"),
    ("under $30", "30"), ("up to thirty dollars", "30"), ("zero dollars", "0"),
])
def test_explicit_budget_normalization(phrase, expected):
    request, _ = normalize(CapturedEvidence(**evidence(budget=phrase)))
    assert str(request.budget) == expected


@pytest.mark.parametrize("phrase,expected", [
    ("six people", 6), ("twenty-one guests", 21), ("one hundred people", 100),
    ("for 6 people", 6),
])
def test_explicit_party_size_normalization(phrase, expected):
    request, _ = normalize(CapturedEvidence(**evidence(party_size=phrase)))
    assert request.party_size == expected


@pytest.mark.parametrize("phrase", [
    "$20 or $40", "twenty or forty dollars", "$20 to thirty dollars",
    "around $40", "a few dollars", "twenty thirty", "$1,00", "1e3",
])
def test_ambiguous_budget_not_selected(phrase):
    request, missing = normalize(CapturedEvidence(**evidence(budget=phrase)))
    assert request.budget is None and "budget" in missing


def test_main_flow_and_authorized_consumer(tmp_path):
    path = tmp_path / "db"
    text = "For six people at a birthday: dry red wine under fifty dollars, no sweet drinks."
    extracted = evidence(budget="under fifty dollars", party_size="six people",
                         occasion="birthday", taste_preferences=["dry", "red wine"],
                         constraints=["no sweet drinks"])
    with TestClient(create_app(path, "fixture", extractor=lambda _: json.dumps(extracted))) as client:
        result = send(client, text)
        assert result.status_code == 201
        body = result.json()
        assert body["needs"]["status"] == "RequestConfirmed"
        assert body["needs"]["budget"] == "50"
        assert body["needs"]["party_size"] == 6
        assert body["missing_fields"] == []
        with sqlite3.connect(path) as db:
            request = read_published_request(db, body["request_id"], RequestConsumer.RECOMMENDATION)
            assert request.budget == 50 and request.status == "RequestAvailable"
            with pytest.raises(PermissionError):
                read_published_request(db, body["request_id"], "browser-supplied-role")


@pytest.mark.parametrize("budget", ["$20 or $40", None])
def test_2a_conflict_preserves_other_clear_fields(tmp_path, budget):
    text = "Budget $20 or $40; red wine."
    extracted = evidence(budget=budget, taste_preferences=["red wine"])
    with TestClient(create_app(tmp_path / "db", "fixture", extractor=lambda _: json.dumps(extracted))) as client:
        body = send(client, text).json()
        assert body["needs"]["budget"] is None
        assert body["needs"]["taste_preferences"] == ["red wine"]
        assert "budget" in body["missing_fields"]


def test_validation_diagnostics_do_not_log_response_values(tmp_path, caplog):
    extracted = evidence(budget=["PRIVATE_RESPONSE_VALUE"])
    extracted["PRIVATE_FIELD_NAME"] = "PRIVATE_EXTRA_VALUE"
    with TestClient(create_app(tmp_path / "db", "fixture",
                              extractor=lambda _: json.dumps(extracted))) as client:
        result = send(client, "red wine")
    assert result.status_code == 502
    assert "Validation diagnostics:" in caplog.text
    assert "string_type" in caplog.text
    assert "extra_forbidden" in caplog.text
    for private in ("PRIVATE_RESPONSE_VALUE", "PRIVATE_FIELD_NAME", "PRIVATE_EXTRA_VALUE"):
        assert private not in caplog.text
        assert private not in result.text


def test_1a_unusable_input_not_published(tmp_path):
    path = tmp_path / "db"
    with TestClient(create_app(path, "fixture", extractor=lambda _: json.dumps(evidence()))) as client:
        body = send(client, "Explain planetary orbits.").json()
        assert body["outcome"] == "incomplete"
        assert body["needs"]["status"] == "RequestUnusable"
        assert len(body["missing_fields"]) == 5
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT count(*) FROM request_inbox").fetchone()[0] == 0


def test_4a_invalid_result_never_reaches_publisher(tmp_path):
    calls = []
    with TestClient(create_app(tmp_path / "db", "fixture",
                              extractor=lambda _: '{"budget":"invented"}',
                              publisher=lambda *args: calls.append(args))) as client:
        assert send(client, "red wine").status_code == 502
        assert calls == []


def test_5a_downstream_failure_preserves_request_and_deduplicates(tmp_path):
    path = tmp_path / "db"
    calls = []
    def unavailable(request_id, request):
        calls.append(request_id)
        request.taste_preferences.clear()  # Consumer cannot mutate the captured record.
        raise ConnectionError("internal error details")
    with TestClient(create_app(path, "fixture",
                              extractor=lambda _: json.dumps(evidence(taste_preferences=["red wine"])),
                              publisher=unavailable)) as client:
        request_id = str(uuid4())
        response = send(client, "red wine", request_id)
        body = response.json()
        assert response.status_code == 201
        assert body["outcome"] == "downstream_unavailable"
        assert body["needs"]["status"] == "DownstreamUnavailable"
        assert body["needs"]["taste_preferences"] == ["red wine"]
        assert "internal error details" not in response.text
        assert client.get(f"/api/requests/{request_id}").json() == body
        assert send(client, "red wine", request_id).json() == body
        assert len(calls) == 1
    with TestClient(create_app(path, "fixture")) as client:
        assert client.get(f"/api/requests/{request_id}").json() == body


def test_original_six_column_database_upgrades_without_losing_data(tmp_path):
    path = tmp_path / "legacy"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE customer_requests (request_id TEXT PRIMARY KEY, text TEXT, needs TEXT, missing_fields TEXT, created_at TEXT, mode TEXT)")
        request_id = str(uuid4())
        db.execute("INSERT INTO customer_requests VALUES (?, ?, ?, ?, ?, ?)",
                   (request_id, "red wine", json.dumps(evidence(taste_preferences="red wine")),
                    "[]", "2026-10-20T00:00:00Z", "fixture"))
    with TestClient(create_app(path, "fixture")) as client:
        body = client.get(f"/api/requests/{request_id}").json()
        assert body["needs"]["taste_preferences"] == ["red wine"]
        assert body["needs"]["status"] == "RequestAvailable"
