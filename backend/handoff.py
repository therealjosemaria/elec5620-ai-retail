"""UC-M1-01 handoff boundary; no downstream business behaviour is executed."""
from enum import StrEnum
from typing import Protocol

from backend.models import CustomerRequest


class RequestConsumer(StrEnum):
    RECOMMENDATION = "drink_recommendation"
    BUDGET_FILTER = "budget_filter"
    CLARIFICATION = "follow_up_clarification"  # Known optional consumer, not implemented.


class RequestPublisher(Protocol):
    def __call__(self, request_id: str, request: CustomerRequest) -> None:
        """Accept a validated request or raise if the service is unavailable."""
        ...


def read_published_request(db, request_id: str, consumer: RequestConsumer) -> CustomerRequest:
    """Internal feature boundary, not an unauthenticated public consumer API.

    Wiring selects the allowed feature identity; never accept a browser-provided role.
    """
    if not isinstance(consumer, RequestConsumer):
        raise PermissionError("Unknown downstream consumer.")
    row = db.execute("SELECT payload FROM request_inbox WHERE request_id=?", (request_id,)).fetchone()
    if row is None:
        raise LookupError("No published request.")
    return CustomerRequest.model_validate_json(row[0])
