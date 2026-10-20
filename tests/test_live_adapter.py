"""Exercise the live adapter with a fake provider; no network or quota usage."""
import json
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
import langchain_openai
from fastapi.testclient import TestClient
from openai import LengthFinishReasonError
from openai.types.chat import ChatCompletion

from backend.main import live_extract, create_app, TruncatedResponseError


def stub_provider(monkeypatch, *, finish="stop"):
    observed = {}
    output = json.dumps(dict(budget=None, party_size=None, occasion=None,
                             taste_preferences=["red wine"], constraints=[]))

    class FakeChat:
        def __init__(self, **kwargs):
            observed["settings"] = kwargs

        def bind(self, **kwargs):
            observed["binding"] = kwargs
            return self

        def invoke(self, messages):
            observed["messages"] = messages
            observed["calls"] = observed.get("calls", 0) + 1
            return SimpleNamespace(content=output,
                                   response_metadata={"finish_reason": finish})

    monkeypatch.setenv("ELEC5620_API_KEY", "fixture-not-a-key")
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChat)
    return observed, output


def test_live_adapter_requests_json_without_retries(monkeypatch):
    observed, output = stub_provider(monkeypatch)
    text = "Red wine, budget either $20 or $40."
    assert live_extract(text) == output
    assert observed["binding"] == {"response_format": {"type": "json_object"}}
    assert observed["settings"]["temperature"] == 0
    assert observed["settings"]["max_retries"] == 0
    assert observed["settings"]["max_tokens"] == 2048
    assert observed["calls"] == 1
    assert observed["messages"][-1].content == text
    assert "Be succinct and professional" in observed["messages"][0].content
    assert "do not paraphrase" in observed["messages"][0].content


@pytest.mark.parametrize("finish", ["length", "content_filter"])
def test_live_adapter_rejects_incomplete_response_without_retry(monkeypatch, finish):
    observed, _ = stub_provider(monkeypatch, finish=finish)
    with pytest.raises(ValueError, match="complete response"):
        live_extract("red wine")
    assert observed["calls"] == 1


@pytest.mark.parametrize("sdk_error", [False, True])
def test_truncated_request_reports_limit_and_never_publishes(tmp_path, sdk_error):
    calls = []
    completion = ChatCompletion(
        id="fixture", created=0, model="fixture", object="chat.completion",
        choices=[{"index": 0, "finish_reason": "length",
                  "message": {"role": "assistant", "content": "PRIVATE_PARTIAL_OUTPUT"}}],
    )

    def extract(text):
        calls.append(text)
        if sdk_error:
            raise LengthFinishReasonError(completion=completion)
        raise TruncatedResponseError("PRIVATE_PARTIAL_OUTPUT")

    path = tmp_path / "db"
    with TestClient(create_app(path, "fixture", extractor=extract)) as client:
        response = client.post("/api/requests", json={
            "request_id": str(uuid4()), "text": "red wine",
        })
    assert response.status_code == 502
    assert "output limit" in response.json()["detail"]
    assert "PRIVATE_PARTIAL_OUTPUT" not in response.text
    assert len(calls) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM customer_requests").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM request_inbox").fetchone()[0] == 0
