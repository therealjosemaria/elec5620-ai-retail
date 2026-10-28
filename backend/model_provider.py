"""University-first Qwen transport with explicit quota-only local fallback."""
from contextlib import closing
from datetime import datetime, timezone
import os

from openai import APIStatusError, LengthFinishReasonError


class ModelText(str):
    def __new__(cls, value, *, provider="university", model="campus-qwen", reason=None):
        result = str.__new__(cls, value)
        result.provider, result.model, result.reason = provider, model, reason
        return result


def complete_json(messages, *, max_tokens, provider="university"):
    from langchain_openai import ChatOpenAI
    local = provider == "local"
    model_name = os.getenv("LOCAL_QWEN_MODEL", "local-qwen") if local else "campus-qwen"
    settings = dict(model=model_name,
        api_key=os.getenv("LOCAL_QWEN_API_KEY", "local-only") if local else os.environ["ELEC5620_API_KEY"],
        base_url=os.getenv("LOCAL_QWEN_BASE_URL", "http://127.0.0.1:18001/v1") if local else os.environ.get("ELEC5620_BASE_URL", "http://10.167.60.148:8000/v1"),
        max_tokens=None, max_retries=0, timeout=120 if local else 30, temperature=0.2,
        # Send the guide's legacy field through extra_body after SDK normalization.
        # The proxy rejects requests containing BOTH token-limit fields.
        extra_body={"max_tokens": max_tokens})
    if not local:
        settings["reasoning_effort"] = "none"
    try:
        response = ChatOpenAI(**settings).bind(response_format={"type": "json_object"}).invoke(messages)
    except LengthFinishReasonError as exc:
        # Metrics only; never log provider text, prompts, headers or credentials.
        import logging
        usage = exc.completion.usage
        details = usage.completion_tokens_details if usage else None
        logging.getLogger(__name__).warning("Model output truncated: provider=%s completion_tokens=%s reasoning_tokens=%s",
            provider, usage.completion_tokens if usage else None,
            details.reasoning_tokens if details else None)
        raise
    if not isinstance(response.content, str) or response.response_metadata.get("finish_reason") not in (None, "stop"):
        raise ValueError("Model did not finish a complete response.")
    return ModelText(response.content, provider=provider, model=model_name)


def is_quota_exhausted(exc):
    if not isinstance(exc, APIStatusError) or exc.status_code not in (403, 429):
        return False
    body = exc.body if isinstance(exc.body, dict) else {}
    error = body.get("error", body)
    code = error.get("code", "") if isinstance(error, dict) else ""
    return isinstance(code, str) and ("quota" in code.lower() or code.lower() in ("budget_exceeded", "insufficient_credits"))


class ModelRouter:
    def __init__(self, connect):
        self.connect = connect
        self.enabled = os.getenv("LOCAL_QWEN_FALLBACK_ENABLED", "false").lower() == "true"

    def choose(self, db, used, limit):
        if not self.enabled:
            return "university"
        row = db.execute("SELECT day FROM model_provider_state WHERE name='university_quota_exhausted'").fetchone()
        if used >= limit or (row and row[0] == datetime.now(timezone.utc).date().isoformat()):
            return "local"
        return "university"

    def invoke(self, messages, *, max_tokens, provider):
        try:
            result = complete_json(messages, max_tokens=max_tokens, provider=provider)
            if provider == "local":
                return ModelText(result, provider=result.provider, model=result.model, reason="university_cap_or_quota_state")
            return result
        except APIStatusError as exc:
            if provider != "university" or not self.enabled or not is_quota_exhausted(exc):
                raise
            with closing(self.connect()) as db, db:
                db.execute("INSERT OR REPLACE INTO model_provider_state VALUES ('university_quota_exhausted', ?)",
                           (datetime.now(timezone.utc).date().isoformat(),))
            result = complete_json(messages, max_tokens=max_tokens, provider="local")
            return ModelText(result, provider=result.provider, model=result.model, reason="university_quota_exhausted")
