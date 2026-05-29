"""Unit tests for is_valid_candidate() in domain/validate.py."""

from __future__ import annotations

from carpix_images.domain.validate import is_valid_candidate


def test_valid_exterior_jpeg_passes() -> None:
    assert (
        is_valid_candidate("File:Toyota_Corolla_2022.jpg", "toyota", "corolla") is True
    )


def test_missing_brand_fails() -> None:
    assert is_valid_candidate("File:Honda_Civic_2021.jpg", "toyota", "corolla") is False


def test_missing_model_fails() -> None:
    assert (
        is_valid_candidate("File:Toyota_Camry_2022.jpg", "toyota", "corolla") is False
    )


def test_non_exterior_keyword_rejects() -> None:
    assert (
        is_valid_candidate("File:BMW_3_Series_interior_2022.jpg", "bmw", "3series")
        is False
    )


def test_badge_keyword_rejects() -> None:
    assert is_valid_candidate("File:Ferrari_488_badge.jpg", "ferrari", "488") is False


def test_special_char_model_normalized() -> None:
    # canonical_key("DM-i") → "dmi"; "File:BYD_Seal_DM-i_2023.jpg" → "bydsealdmi2023jpg"
    assert is_valid_candidate("File:BYD_Seal_DM-i_2023.jpg", "byd", "DM-i") is True


def test_plan_keyword_rejects() -> None:
    assert (
        is_valid_candidate(
            "File:BMW_3series_plan_in_BMW-Museum_in_Munich.jpg", "bmw", "3series"
        )
        is False
    )


def test_museum_keyword_rejects() -> None:
    assert (
        is_valid_candidate(
            "File:BMW_3series_in_BMW-Museum_Munich.jpg", "bmw", "3series"
        )
        is False
    )


def test_empty_title_fails() -> None:
    assert is_valid_candidate("", "toyota", "corolla") is False
