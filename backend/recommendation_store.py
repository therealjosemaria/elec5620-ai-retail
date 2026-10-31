"""Durable at-most-once recommendation generation, including failures and concurrency."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import os
from uuid import UUID

from backend.models import CustomerRequest, Product, RequestStatus
from backend.qwen_recommendations import GroundingError, live_recommend, validate_choices
from pydantic import ValidationError
from backend.recommendations import RecommendationOutcome, RecommendationResult, recommend_drinks, combined_preferences


class RecommendationError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


class SavedRecommendations(RecommendationResult):
    request_id: UUID
    mode: str
    created_at: datetime
    catalogue_digest: str
    cache_hit: bool = False
    model_provider: str = "fixture"
    model_name: str | None = None
    fallback_reason: str | None = None
    revalidated_offline: bool = False
    preference_validation_version: int = 0


def ensure_recommendation_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS recommendation_results (
            request_id TEXT PRIMARY KEY, mode TEXT NOT NULL,
            status TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workflow_runs (
            workflow_id TEXT PRIMARY KEY, request_id TEXT,
            kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_provider_state (name TEXT PRIMARY KEY, day TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS model_call_results (
            attempt_id TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT,
            fallback_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS recommendation_raw (
            request_id TEXT PRIMARY KEY, raw TEXT NOT NULL, needs TEXT NOT NULL,
            catalogue TEXT NOT NULL, provider TEXT NOT NULL, model TEXT,
            fallback_reason TEXT, catalogue_digest TEXT NOT NULL
        );
    """)


class RecommendationStore:
    def __init__(self, connect, *, mode, daily_limit, generator=None, router=None):
        self.connect, self.mode, self.limit = connect, mode, daily_limit
        self.generator = generator
        self.router = router

    def revalidate(self, request_id):
        """Explicit developer action: validate retained output, never contact any model."""
        with closing(self.connect()) as db:
            job = db.execute("SELECT mode,status,created_at FROM recommendation_results WHERE request_id=?", (str(request_id),)).fetchone()
            raw = db.execute("SELECT raw,needs,catalogue,provider,model,fallback_reason,catalogue_digest FROM recommendation_raw WHERE request_id=?", (str(request_id),)).fetchone()
            inbox = db.execute("SELECT payload FROM request_inbox WHERE request_id=?", (str(request_id),)).fetchone()
        if job is None or job[1] != "failed" or raw is None or inbox is None:
            raise RecommendationError(409, "Offline validation requires a failed result with retained complete output and a published request.")
        needs = CustomerRequest.model_validate_json(raw[1])
        if CustomerRequest.model_validate_json(inbox[0]) != needs:
            raise RecommendationError(409, "Published needs changed; retained output was not republished.")
        products = [Product.model_validate(p) for p in json.loads(raw[2])]
        digest = sha256(json.dumps([p.model_dump(mode="json") for p in products], sort_keys=True).encode()).hexdigest()
        if digest != raw[6]:
            raise RecommendationError(409, "Retained catalogue snapshot failed its integrity check.")
        result = validate_choices(raw[0], needs, products)
        if raw[3] == "local":
            result.method = "local_qwen_catalogue_recommendation"
        saved = SavedRecommendations(**result.model_dump(), preference_validation_version=2, request_id=request_id, mode=job[0], created_at=job[2],
            catalogue_digest=digest, model_provider=raw[3], model_name=raw[4], fallback_reason=raw[5], revalidated_offline=True)
        with closing(self.connect()) as db, db:
            changed = db.execute("UPDATE recommendation_results SET status='saved',payload=? WHERE request_id=? AND status='failed'",
                                 (saved.model_dump_json(), str(request_id))).rowcount
            if changed != 1:
                raise RecommendationError(409, "Result state changed during offline validation.")
            db.execute("UPDATE attempts SET status='saved' WHERE request_id=?", ("recommendation:" + str(request_id),))
        return saved

    def read(self, request_id, *, required=True):
        with closing(self.connect()) as db:
            row = db.execute("SELECT status,payload FROM recommendation_results WHERE request_id=?", (str(request_id),)).fetchone()
        if row is None:
            if required:
                raise RecommendationError(409, "Generate recommendations first; no model call was made by this read.")
            return None
        if row[0] != "saved":
            raise RecommendationError(409, "Recommendation generation is pending or failed. No automatic retry; start a new customer request for another intentional attempt.")
        saved = SavedRecommendations.model_validate_json(row[1])
        if saved.preference_validation_version < 2:
            with closing(self.connect()) as db:
                inbox = db.execute("SELECT payload FROM request_inbox WHERE request_id=?", (str(request_id),)).fetchone()
            if inbox is None:
                raise RecommendationError(409, "Saved needs unavailable; cached recommendations cannot be safely revalidated. No model call made.")
            saved = combined_preferences(CustomerRequest.model_validate_json(inbox[0]), saved).model_copy(
                update={"preference_validation_version": 2, "revalidated_offline": True})
            with closing(self.connect()) as db, db:
                db.execute("UPDATE recommendation_results SET payload=? WHERE request_id=? AND status='saved' AND payload=?",
                           (saved.model_dump_json(), str(request_id), row[1]))
        return saved.model_copy(update={"cache_hit": True})

    def generate(self, request_id, request: CustomerRequest, load_catalogue):
        if cached := self.read(request_id, required=False):
            return cached
        try:
            products = [Product.model_validate(p) for p in load_catalogue()]
            if (len({p.product_id for p in products}) != len(products)
                    or any(not p.product_id.strip() or p.price < 0 or not 0 <= p.abv <= 100 for p in products)):
                raise ValueError("Invalid catalogue")
        except Exception:
            raise RecommendationError(503, "Authorised catalogue is unavailable or invalid; no model call made.")
        unusable = request.status in (RequestStatus.UNUSABLE, RequestStatus.VALIDATION_FAILED) or not any(
            (request.taste_preferences, request.constraints, request.occasion, request.party_size is not None))
        uses_model = not unusable and bool(products) and (self.mode == "live" or self.generator is not None)
        now = datetime.now(timezone.utc)
        catalogue_digest = sha256(json.dumps([p.model_dump(mode="json") for p in products], sort_keys=True).encode()).hexdigest()
        attempt_id = "recommendation:" + str(request_id)
        provider = "university"
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM recommendation_results WHERE request_id=?", (str(request_id),)).fetchone():
                # Another process reserved it while this caller loaded the catalogue.
                return self.read(request_id)
            if uses_model and self.mode == "live":
                used = db.execute("SELECT count(*) FROM attempts WHERE mode='live' AND day=?", (now.date().isoformat(),)).fetchone()[0]
                if self.router is not None and self.generator is None:
                    provider = self.router.choose()
                if provider == "university" and self.generator is None and not os.getenv("ELEC5620_API_KEY"):
                    raise RecommendationError(503, "Backend API key is not configured; no model call made.")
                if self.limit is not None and used >= self.limit:
                    raise RecommendationError(429, "Local daily live-call limit reached. No model call was made.")
                db.execute("INSERT INTO attempts VALUES (?, ?, ?, ?, 'pending')",
                    (attempt_id, catalogue_digest, "local" if provider == "local" else "live", now.date().isoformat()))
            db.execute("INSERT INTO recommendation_results VALUES (?, ?, 'pending', NULL, ?)",
                       (str(request_id), self.mode, now.isoformat()))
        # Reservation is committed before the external call; never retry on ambiguity/crash.
        try:
            raw = None
            if unusable:
                result = RecommendationResult(outcome=RecommendationOutcome.UNUSABLE_REQUEST,
                    limitations=["No usable stated needs; no model call made."], method="no_model_call")
            elif not products:
                result = RecommendationResult(outcome=RecommendationOutcome.NO_MATCH,
                    limitations=["Authorised catalogue is empty; no model call made."], method="no_model_call")
            elif uses_model:
                needs_copy, products_copy = request.model_copy(deep=True), [p.model_copy(deep=True) for p in products]
                raw = (self.generator(needs_copy, products_copy) if self.generator is not None else
                       live_recommend(needs_copy, products_copy, provider=provider, router=self.router))
                # Private, ignored database only. Never returned by a public endpoint.
                # Retain complete untrusted output so validation can be diagnosed offline.
                with closing(self.connect()) as db, db:
                    db.execute("INSERT INTO recommendation_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(request_id), str(raw), request.model_dump_json(),
                         json.dumps([p.model_dump(mode="json") for p in products]),
                         getattr(raw, "provider", "injected"), getattr(raw, "model", None),
                         getattr(raw, "reason", None), catalogue_digest))
                result = validate_choices(raw, request, products)
                if getattr(raw, "provider", None) == "local":
                    result.method = "local_qwen_catalogue_recommendation"
            else:
                result = recommend_drinks(request, lambda: products).model_copy(update={"method": "fixture_catalogue_match"})
            saved = SavedRecommendations(**result.model_dump(), preference_validation_version=2, request_id=request_id, mode=self.mode,
                created_at=now, catalogue_digest=catalogue_digest,
                model_provider=getattr(raw, "provider", "injected" if raw is not None else
                                       ("fixture" if result.method == "fixture_catalogue_match" else "none")),
                model_name=getattr(raw, "model", None), fallback_reason=getattr(raw, "reason", None))
            with closing(self.connect()) as db, db:
                db.execute("UPDATE recommendation_results SET status='saved',payload=? WHERE request_id=?",
                           (saved.model_dump_json(), str(request_id)))
                db.execute("UPDATE attempts SET status='saved' WHERE request_id=?", (attempt_id,))
            return saved
        except Exception as exc:
            logging.getLogger(__name__).warning("Recommendation generation failed (%s)", type(exc).__name__)
            if isinstance(exc, GroundingError):
                logging.getLogger(__name__).warning("Recommendation grounding check: %s", str(exc))
            elif isinstance(exc, ValidationError):
                allowed = {"recommendations", "unresolved_needs", "product_id", "rank", "matches",
                           "need_field", "need_value", "catalogue_field", "catalogue_value"}
                diagnostics = [{"field": [part if isinstance(part,int) or part in allowed else "response" for part in error["loc"]],
                                "code": error["type"]} for error in exc.errors(include_input=False,include_context=False,include_url=False)]
                logging.getLogger(__name__).warning("Recommendation schema checks: %s", diagnostics)
            with closing(self.connect()) as db, db:
                db.execute("UPDATE recommendation_results SET status='failed' WHERE request_id=?", (str(request_id),))
                db.execute("UPDATE attempts SET status='failed' WHERE request_id=?", (attempt_id,))
            raise RecommendationError(502, "Recommendation generation failed or returned invalid catalogue evidence. No result published and no automatic retry.")
