"""Evidence validation and conservative normalization for M1-AR-01 only."""
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, field_validator

from backend.models import CustomerRequest

FIELDS = ("budget", "party_size", "occasion", "taste_preferences", "constraints")
SMALL = dict(zip(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(),
    range(20),
))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))


def word_integer(words: list[str]) -> int | None:
    """Parse explicit English cardinal numbers; reject malformed combinations."""
    if "thousand" in words:
        if words.count("thousand") != 1:
            return None
        i = words.index("thousand")
        left, right = word_integer(words[:i]), words[i + 1:]
        if right[:1] == ["and"]:
            right = right[1:]
        rest = word_integer(right) if right else 0
        return left * 1000 + rest if left and left < 1000 and rest is not None and rest < 1000 else None
    if "hundred" in words:
        if len(words) < 2 or words[1] != "hundred" or SMALL.get(words[0], 0) not in range(1, 10):
            return None
        right = words[2:]
        if right[:1] == ["and"]:
            right = right[1:]
        rest = word_integer(right) if right else 0
        return SMALL[words[0]] * 100 + rest if rest is not None and rest < 100 else None
    if len(words) == 1:
        return SMALL.get(words[0], TENS.get(words[0]))
    if len(words) == 2 and words[0] in TENS and SMALL.get(words[1], 0) in range(1, 10):
        return TENS[words[0]] + SMALL[words[1]]
    return None


class CapturedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    budget: str | None
    party_size: str | None
    occasion: str | None
    # Strings remain accepted for first-slice stored records and the tested proxy response.
    taste_preferences: list[str] | str | None
    constraints: list[str] | str | None

    @field_validator("*")
    @classmethod
    def nonempty(cls, value):
        values = value if isinstance(value, list) else [value]
        for item in values:
            if item is not None and (not item.strip() or len(item) > 1000):
                raise ValueError("Evidence must contain bounded, nonempty text.")
        return value

    def validate_source(self, text: str):
        for value in self.model_dump().values():
            values = value if isinstance(value, list) else [value]
            if any(item is not None and item not in text for item in values):
                raise ValueError("Captured evidence is not present in the request.")


def numeric_value(evidence: str | None, *, integer=False):
    """Normalize one stated amount/count, never choose among ranges or alternatives."""
    if evidence is None:
        return None
    text = evidence.lower().strip()
    if re.search(r"\b(or|between|roughly|about|around|approximately)\b", text):
        return None
    if re.search(r"\d.*\bto\b", text):
        return None
    tokens = re.findall(r"(?<!\w)[+-]?\d[\w,.]*", text)
    if tokens:
        if len(tokens) != 1:
            return None
        token = tokens[0].rstrip(".")
        if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?[k]?", token):
            return None
        number = Decimal(token.rstrip("k").replace(",", ""))
        if token.endswith("k"):
            number *= 1000
    else:
        # Remove context words, not number words; do not interpret "a few"/"a couple".
        text = re.sub(r"\b(?:budget|of|under|up|to|less|than|at|most|maximum|limit|"
                      r"for|party|group|people|persons|guests|person|dollars|dollar|"
                      r"aud|usd|eur|gbp|is)\b", " ", text)
        words = re.sub(r"[$€£-]", " ", text).split()
        if words.count("point") == 1:
            i = words.index("point")
            whole = word_integer(words[:i])
            digits = words[i + 1:]
            if whole is None or not digits or any(SMALL.get(w, 99) > 9 for w in digits):
                return None
            number = Decimal(f"{whole}." + "".join(str(SMALL[w]) for w in digits))
        else:
            whole = word_integer(words)
            if whole is None:
                return None
            number = Decimal(whole)
    if integer:
        return int(number) if number == number.to_integral_value() else None
    return number


def normalize(evidence: CapturedEvidence) -> tuple[CustomerRequest, list[str]]:
    def items(value):
        return value if isinstance(value, list) else ([] if value is None else [value])
    request = CustomerRequest(
        budget=numeric_value(evidence.budget),
        party_size=numeric_value(evidence.party_size, integer=True),
        occasion=evidence.occasion,
        taste_preferences=items(evidence.taste_preferences),
        constraints=items(evidence.constraints),
    )
    missing = [name for name in FIELDS if getattr(request, name) in (None, [])]
    return request, missing
