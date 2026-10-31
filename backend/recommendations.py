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
from backend.servings import MARKER, serving_note


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
    "sweet red wine": (("category", "wine"), ("flavour_tags", "red"), ("sweetness", "sweet")),
    "dry red wine": (("category", "wine"), ("flavour_tags", "red"), ("sweetness", "dry")),
    **{tag: (("flavour_tags", tag),) for tag in
       ("red", "white", "plum", "oak", "cherry", "light", "citrus", "sparkling", "fruity", "hoppy")},
    "no sweet drinks": (("sweetness", "dry"),),
    "not sweet": (("sweetness", "dry"),),
    "dry drinks": (("sweetness", "dry"),),
}


def _phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold()).rstrip(".!。")


SUITABILITY_LIMITATION = (
    "Occasion and party size were captured where stated. Occasion is retained as context, "
    "not a verified catalogue suitability claim. Party coverage assumes one serving per person "
    "using the explicitly labelled prototype package estimates."
)


def combined_preferences(request: CustomerRequest, result: RecommendationResult) -> RecommendationResult:
    """§10.3: a candidate must satisfy the combined needs, not a separate subset.

    Known phrases are checked against actual facts. Broader language still needs
    model evidence for each preference; this does not claim general semantic proof.
    Also used when reading old cached results, without another model call.
    """
    needs = list(dict.fromkeys(request.taste_preferences + request.constraints))
    kept = []
    for recommendation in result.recommendations:
        product = recommendation.product
        evidence = list(recommendation.matched_needs)
        explanations = [recommendation.explanation]
        for need in needs:
            predicates = PHRASES.get(_phrase(need))
            if predicates is None:
                if need not in evidence:
                    break
                continue
            def matches(field, value):
                actual = getattr(product, field)
                facts = actual if isinstance(actual, list) else [str(actual)]
                return value in {fact.casefold() for fact in facts}
            if not all(matches(field, value) for field, value in predicates):
                break
            if need not in evidence:
                facts = ", ".join(f"{field.replace('_', ' ')}: {value}" for field, value in predicates)
                explanations.append(f'Your stated need "{need}" matches catalogue {facts}.')
                evidence.append(need)
        else:
            if request.party_size is not None:
                # Revalidation of a cached result must not duplicate the note.
                explanations = [text.split(MARKER, 1)[0].strip() for text in explanations]
                explanations.append(serving_note(product, request.party_size))
            kept.append(recommendation.model_copy(update={
                "matched_needs": evidence, "explanation": " ".join(explanations)}))
    captured_only = {request.occasion, str(request.party_size) if request.party_size is not None else None} - {None}
    captured_warnings = {f'Catalogue evidence did not resolve the stated need: "{value}".'
                         for value in captured_only}
    limits = [line for line in result.limitations
              if not line.startswith("Catalogue has no occasion or party-size suitability")
              and line not in captured_warnings
              and not line.startswith("Occasion and party size were captured where stated.")
              and line != "Occasion and party size were captured where stated, but catalogue data cannot assess their suitability."]
    if request.occasion is not None or request.party_size is not None:
        if SUITABILITY_LIMITATION not in limits:
            limits.append(SUITABILITY_LIMITATION)
    if not kept and needs and result.outcome in {RecommendationOutcome.COMPLETE, RecommendationOutcome.NO_MATCH}:
        limits.append("No supported catalogue match for the combined stated preferences and constraints; partial matches are not offered as suitable recommendations.")
    outcome = result.outcome
    if outcome == RecommendationOutcome.COMPLETE and not kept:
        outcome = RecommendationOutcome.NO_MATCH
    return result.model_copy(update={"recommendations": kept, "limitations": list(dict.fromkeys(limits)), "outcome": outcome})


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
        limitations.append(SUITABILITY_LIMITATION)
    if not results:
        limitations.append("No catalogue product satisfies all supported stated preferences and constraints.")
    return combined_preferences(request, RecommendationResult(
        outcome=RecommendationOutcome.COMPLETE if results else RecommendationOutcome.NO_MATCH,
        recommendations=results, limitations=limitations))
