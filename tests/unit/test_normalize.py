"""Unit tests for canonical_key normalization — NORM-01."""

import pytest

from carpix_images.domain.normalize import canonical_key


@pytest.mark.parametrize(
    "input,expected",
    [
        ("Toyota", "toyota"),
        ("BYD DM-i", "byddmi"),
        ("Land Rover", "landrover"),
        ("Alfa-Romeo", "alfaromeo"),
        ("Model 3", "model3"),
        ("", ""),
    ],
)
def test_canonical_key(input: str, expected: str) -> None:
    assert canonical_key(input) == expected


class TestCanonicalKey:
    def test_output_is_lowercase(self) -> None:
        result = canonical_key("Toyota Camry")
        assert result == result.lower()

    def test_dm_i_variants_are_equivalent(self) -> None:
        assert canonical_key("DM-i") == canonical_key("Dmi")
        assert canonical_key("Dmi") == canonical_key("DMi")
        assert canonical_key("DM-i") == canonical_key("DM i")
