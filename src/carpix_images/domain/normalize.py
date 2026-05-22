from __future__ import annotations

import re


def canonical_key(value: str) -> str:
    """Compact identity key for cache/coalescing lookups.

    Removes all non-alphanumeric characters and lowercases, so
    'DM-i', 'DMi', 'Dmi', and 'DM i' all map to 'dmi'.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())
