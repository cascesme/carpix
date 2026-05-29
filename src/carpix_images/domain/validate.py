from __future__ import annotations

from carpix_images.domain.normalize import canonical_key

NON_EXTERIOR_KEYWORDS: frozenset[str] = frozenset(
    {
        "interior",
        "engine",
        "badge",
        "emblem",
        "logo",
        "dashboard",
        "cockpit",
        "cabin",
        "instrument",
        "steering",
        "seat",
        "trunk",
        "plan",
        "museum",
        "exhibition",
        "timeline",
        "diagram",
        "schematic",
    }
)


def is_valid_candidate(file_title: str, brand: str, model: str) -> bool:
    title_norm = canonical_key(file_title)
    if not title_norm:
        return False
    brand_norm = canonical_key(brand)
    model_norm = canonical_key(model)
    if brand_norm and brand_norm not in title_norm:
        return False
    if model_norm and model_norm not in title_norm:
        return False
    return not any(kw in title_norm for kw in NON_EXTERIOR_KEYWORDS)
