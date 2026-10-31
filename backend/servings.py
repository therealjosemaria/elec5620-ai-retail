"""Explicit prototype pours, separate from Australian standard drinks (10 g).

No catalogue/schema changes. ABV always comes from the authorised product.
"""
from decimal import Decimal, ROUND_HALF_UP
import re

from backend.models import Product

MARKER = "Prototype serving estimate:"


def package_details(product: Product):
    category = product.category.casefold()
    name = product.name.casefold()
    sizes = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*ml\b", name)
    assumed = False
    # The seed catalogue specifies a six-pack but omits container volume.
    if category == "beer" and name == "pale ale 6-pack" and not sizes:
        sizes = ["375"]
        assumed = True
    if len(sizes) != 1 or category not in {"wine", "beer", "spirits"}:
        return None
    volume = Decimal(sizes[0])
    if volume <= 0 or not product.abv.is_finite() or not 0 <= product.abv <= 100:
        return None
    packs = re.findall(r"\b(\d+)\s*-?\s*pack\b", name)
    if len(packs) > 1:
        return None
    count = int(packs[0]) if packs else 1
    if count <= 0:
        return None
    pour = Decimal("150") if category == "wine" else Decimal("30") if category == "spirits" else volume
    return volume, pour, count, assumed


def servings_per_package(product: Product) -> int | None:
    details = package_details(product)
    if details is None:
        return None
    volume, pour, count, _ = details
    return int(volume // pour) * count


def serving_note(product: Product, party_size: int | None = None) -> str:
    details = package_details(product)
    if details is None:
        return f"{MARKER} unavailable: package volume, ABV or serving rule is not established; this does not invalidate the preference match."
    volume, pour, count, assumed = details
    per_container = int(volume // pour)
    full_pours = per_container * count
    remainder = (volume % pour) * count
    std = (volume * count / Decimal("1000") * product.abv * Decimal("0.789")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP)
    package = f"{count} x {volume:g} ml containers" if count > 1 else f"{volume:g} ml bottle"
    basis = " (375 ml per beer container is an explicit prototype assumption)" if assumed else ""
    leftover = f", with {remainder:g} ml left over" if remainder else ""
    coverage = ""
    if party_size is not None:
        if party_size <= 0:
            coverage = " A positive party size is required to assess package coverage."
        elif full_pours >= party_size:
            coverage = (f" Assuming one {pour:g} ml serving per person, one package covers "
                        f"the stated {party_size} people; this does not assume everyone consumes all remaining servings.")
        else:
            coverage = (f" Assuming one {pour:g} ml serving per person, one package does not cover "
                        f"the stated {party_size} people; additional package quantity and total cost are not established.")
    return (f"{MARKER} {package}{basis}; assuming {pour:g} ml per serving, "
            f"{full_pours} full servings{leftover}. At catalogue ABV {product.abv:g}%, "
            f"approximately {std} Australian standard drinks in the whole package. "
            "Servings are not standard drinks; this is not a per-person consumption recommendation." + coverage)
