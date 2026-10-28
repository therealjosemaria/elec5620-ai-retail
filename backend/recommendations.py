"""Member 2 / UC-M2-01 (§6.2.1, §10.3, Figure 4).

Conservative, deterministic prototype matcher. Unsupported language is explicit;
this is not a live LLM evaluator. Catalogue facts always come from the repository.
"""
from collections.abc import Callable, Iterable
from enum import StrEnum
import logging
import re

from pydantic import Field

from backend.models import CustomerRequest, DomainModel, Product, RequestStatus


class RecommendationOutcome(StrEnum):
    COMPLETE = "complete"
    UNUSABLE_REQUEST = "unusable_request"
    UNSUPPORTED_REQUEST = "unsupported_request"
    SOURCE_UNAVAILABLE = "source_unavailable"
    NO_MATCH = "no_match"


class DrinkRecommendation(DomainModel):
    rank: int
    product: Product
    explanation: str
    matched_needs: list[str]


class RecommendationResult(DomainModel):
    outcome: RecommendationOutcome
    recommendations: list[DrinkRecommendation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    method: str = "deterministic_catalogue_match"


# Exact phrase support deliberately avoids treating 'not red wine' as 'red wine'.
# A phrase compiles to predicates over catalogue facts, never over inventory/price.
PHRASES = {
    "wine": (("category", "wine"),),
    "red wine": (("category", "wine"), ("flavour_tags", "red")),
    "white wine": (("category", "wine"), ("flavour_tags", "white")),
    "beer": (("category", "beer"),),
    "spirits": (("category", "spirits"),),
    "dry": (("sweetness", "dry"),),
    "dry wine": (("category", "wine"), ("sweetness", "dry")),
    "sweet": (("sweetness", "sweet"),),
    "sweet wine": (("category", "wine"), ("sweetness", "sweet")),
    **{tag: (("flavour_tags", tag),) for tag in
       ("red", "white", "plum", "oak", "cherry", "light", "citrus", "sparkling", "fruity", "hoppy")},
    "no sweet drinks": (("sweetness", "dry"),),
    "not sweet": (("sweetness", "dry"),),
    "dry drinks": (("sweetness", "dry"),),
}


def _phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold()).rstrip(".!。")


def recommend_drinks(request: CustomerRequest,
                     load_catalogue: Callable[[], Iterable[Product]]) -> RecommendationResult:
    """All explicit supported taste/constraint phrases must match (equal ranks allowed).

    Occasion and party size are preserved upstream but do not justify invented
    catalogue suitability or quantities. Budget belongs to Member 4.
    """
    needs = list(dict.fromkeys(request.taste_preferences + request.constraints))
    if request.status in {RequestStatus.UNUSABLE, RequestStatus.VALIDATION_FAILED} or not needs:
        return RecommendationResult(outcome=RecommendationOutcome.UNUSABLE_REQUEST,
                                    limitations=["This matcher needs a stated taste or product constraint."])
    unsupported = [need for need in needs if _phrase(need) not in PHRASES]
    if unsupported:
        return RecommendationResult(outcome=RecommendationOutcome.UNSUPPORTED_REQUEST,
                                    limitations=["Prototype matcher cannot safely interpret: " + "; ".join(unsupported)])
    try:
        products = [Product.model_validate(p) for p in load_catalogue()]
        if len({p.product_id for p in products}) != len(products):
            raise ValueError("Duplicate catalogue IDs")
        if any(not p.product_id.strip() or not p.name.strip() or p.price < 0 or not 0 <= p.abv <= 100
               for p in products):
            raise ValueError("Invalid catalogue facts")
    except Exception as exc:
        logging.getLogger(__name__).warning("Recommendation catalogue unavailable (%s)", type(exc).__name__)
        return RecommendationResult(outcome=RecommendationOutcome.SOURCE_UNAVAILABLE,
                                    limitations=["Catalogue unavailable or invalid; no product was invented."])

    def matches(product, field, value):
        actual = getattr(product, field)
        return value in {v.casefold() for v in actual} if isinstance(actual, list) else actual.casefold() == value

    results = []
    for product in sorted(products, key=lambda p: p.product_id):
        if not all(matches(product, field, value)
                   for need in needs for field, value in PHRASES[_phrase(need)]):
            continue
        evidence = []
        for need in needs:
            facts = ", ".join(f"{field.replace('_', ' ')}: {value}" for field, value in PHRASES[_phrase(need)])
            evidence.append(f'Your stated need "{need}" matches catalogue {facts}.')
        # Every candidate meets all stated predicates: no evidence to claim one is better.
        results.append(DrinkRecommendation(rank=1, product=product, matched_needs=needs,
                                          explanation=" ".join(evidence)))
    limitations = ["Rule-based prototype; equal matches share rank 1. Product ID only orders the display.",
                   "Budget and current availability have not been checked."]
    if request.occasion is not None or request.party_size is not None:
        limitations.append("Catalogue has no occasion or party-size suitability data; these fields do not affect ranking.")
    if not results:
        limitations.append("No catalogue product satisfies all supported stated preferences and constraints.")
    return RecommendationResult(outcome=RecommendationOutcome.COMPLETE if results else RecommendationOutcome.NO_MATCH,
                                recommendations=results, limitations=limitations)
