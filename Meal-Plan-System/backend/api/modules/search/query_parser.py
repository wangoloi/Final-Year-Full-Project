"""
Parse user search intent into a clean text query + nutrition filters.

We keep this logic backend-side so it works for both Typesense and SQL fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NutritionFilters:
    # Numeric filters are interpreted as grams per serving/row as stored in DB.
    carbs_max: Optional[float] = None
    carbs_min: Optional[float] = None
    sugar_max: Optional[float] = None
    sugar_min: Optional[float] = None
    gi_max: Optional[int] = None
    gi_min: Optional[int] = None


_LOW_WORDS = r"(low|lower|less|light)"
_HIGH_WORDS = r"(high|higher|more|rich)"
_CARB_WORDS = r"(carb|carbs|carbohydrate|carbohydrates)"
_SUGAR_WORDS = r"(sugar|sugars|glucose)"
_GI_WORDS = r"(gi|glycemic\s*index|glycaemic\s*index|glycemic)"


def _strip_phrases(text: str, patterns: list[str]) -> str:
    out = text
    for p in patterns:
        out = re.sub(p, " ", out, flags=re.I)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def parse_search_query(raw: str) -> tuple[str, NutritionFilters]:
    """
    Return (text_query, filters).

    Examples:
      "low carbs beans" -> ("beans", carbs_max=15)
      "high gi rice" -> ("rice", gi_min=70)
      "low sugar fruits" -> ("fruits", sugar_max=5, gi_max=55)  (sugar often implies GI intent)
    """
    q = (raw or "").strip()
    if not q:
        return "", NutritionFilters()

    lowered = q.lower()
    f = NutritionFilters()

    # Thresholds (simple heuristics; can be tuned)
    LOW_CARBS_MAX = 15.0
    HIGH_CARBS_MIN = 30.0
    LOW_SUGAR_MAX = 5.0
    HIGH_SUGAR_MIN = 15.0
    LOW_GI_MAX = 55
    HIGH_GI_MIN = 70

    def has(pattern: str) -> bool:
        return re.search(pattern, lowered, flags=re.I) is not None

    # Carbs intent
    if has(rf"\b{_LOW_WORDS}\s+{_CARB_WORDS}\b") or has(rf"\b{_CARB_WORDS}\s+{_LOW_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "carbs_max": LOW_CARBS_MAX})
    if has(rf"\b{_HIGH_WORDS}\s+{_CARB_WORDS}\b") or has(rf"\b{_CARB_WORDS}\s+{_HIGH_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "carbs_min": HIGH_CARBS_MIN})

    # Sugar intent
    if has(rf"\b{_LOW_WORDS}\s+{_SUGAR_WORDS}\b") or has(rf"\b{_SUGAR_WORDS}\s+{_LOW_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "sugar_max": LOW_SUGAR_MAX, "gi_max": f.gi_max or LOW_GI_MAX})
    if has(rf"\b{_HIGH_WORDS}\s+{_SUGAR_WORDS}\b") or has(rf"\b{_SUGAR_WORDS}\s+{_HIGH_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "sugar_min": HIGH_SUGAR_MIN, "gi_min": f.gi_min or HIGH_GI_MIN})

    # GI intent
    if has(rf"\b{_LOW_WORDS}\s+{_GI_WORDS}\b") or has(rf"\b{_GI_WORDS}\s+{_LOW_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "gi_max": LOW_GI_MAX})
    if has(rf"\b{_HIGH_WORDS}\s+{_GI_WORDS}\b") or has(rf"\b{_GI_WORDS}\s+{_HIGH_WORDS}\b"):
        f = NutritionFilters(**{**f.__dict__, "gi_min": HIGH_GI_MIN})

    # Remove intent phrases from the text query; keep the remaining food term(s)
    cleaned = _strip_phrases(
        q,
        [
            rf"\b{_LOW_WORDS}\s+{_CARB_WORDS}\b",
            rf"\b{_HIGH_WORDS}\s+{_CARB_WORDS}\b",
            rf"\b{_LOW_WORDS}\s+{_SUGAR_WORDS}\b",
            rf"\b{_HIGH_WORDS}\s+{_SUGAR_WORDS}\b",
            rf"\b{_LOW_WORDS}\s+{_GI_WORDS}\b",
            rf"\b{_HIGH_WORDS}\s+{_GI_WORDS}\b",
            rf"\b{_CARB_WORDS}\s+{_LOW_WORDS}\b",
            rf"\b{_CARB_WORDS}\s+{_HIGH_WORDS}\b",
            rf"\b{_SUGAR_WORDS}\s+{_LOW_WORDS}\b",
            rf"\b{_SUGAR_WORDS}\s+{_HIGH_WORDS}\b",
            rf"\b{_GI_WORDS}\s+{_LOW_WORDS}\b",
            rf"\b{_GI_WORDS}\s+{_HIGH_WORDS}\b",
        ],
    )

    return cleaned, f

