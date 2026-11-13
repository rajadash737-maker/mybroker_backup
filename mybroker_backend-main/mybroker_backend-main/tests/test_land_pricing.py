from decimal import Decimal

import pytest

from app.sell_land.constants import AreaUnit
from app.sell_land.pricing import (
    SQFT_PER_UNIT,
    area_to_sqft,
    calculate_total_price,
    price_label,
    rate_from_price_per_sqft,
    rate_to_price_per_sqft,
)


@pytest.mark.parametrize(
    ("unit", "factor", "label"),
    [
        (AreaUnit.SQFT, Decimal("1"), "Price per Sq.ft"),
        (AreaUnit.SQM, Decimal("10.7639104167"), "Price per Sq.m"),
        (AreaUnit.DECIMAL, Decimal("435.6"), "Price per Decimal"),
        (AreaUnit.ACRE, Decimal("43560"), "Price per Acre"),
        (AreaUnit.HECTARE, Decimal("107639.104167"), "Price per Hectare"),
    ],
)
def test_supported_unit_factor_area_conversion_and_label(unit, factor, label):
    assert SQFT_PER_UNIT[unit] == factor
    assert area_to_sqft("1.25", unit) == Decimal("1.25") * factor
    assert price_label(unit) == label


@pytest.mark.parametrize("unit", list(AreaUnit)[:5])
def test_fractional_rate_normalization_and_round_trip(unit):
    entered_rate = Decimal("123.456789")
    normalized_rate = rate_to_price_per_sqft(entered_rate, unit)

    assert isinstance(normalized_rate, Decimal)
    restored_rate = rate_from_price_per_sqft(normalized_rate, unit)
    assert abs(restored_rate - entered_rate) <= Decimal("1e-24")


def test_fractional_area_and_rate_total_uses_decimal_arithmetic():
    converted_area = area_to_sqft("2.75", "decimal")
    normalized_rate = rate_to_price_per_sqft("0.125", "decimal")
    expected_total = Decimal("0.34375")

    assert converted_area == Decimal("2.75") * Decimal("435.6")
    total = calculate_total_price(converted_area, normalized_rate)
    assert abs(total - expected_total) <= Decimal("1e-48")


def test_decimal_regression_fractional_total_avoids_default_context_error():
    area_sqft = area_to_sqft("2.75", AreaUnit.DECIMAL)
    normalized_rate = rate_to_price_per_sqft("0.125", AreaUnit.DECIMAL)

    total = calculate_total_price(area_sqft, normalized_rate)

    assert total != Decimal("0.3437500000000000000000000001")
    assert abs(total - Decimal("0.34375")) <= Decimal("1e-48")


def test_rejects_legacy_bigha_conversion_without_invented_factor():
    with pytest.raises(ValueError, match="Unsupported land area unit"):
        area_to_sqft(1, AreaUnit.BIGHA)

    with pytest.raises(ValueError, match="Unsupported land area unit"):
        price_label(AreaUnit.BIGHA)


def test_rejects_unknown_unit_clearly():
    with pytest.raises(ValueError, match="Unsupported land area unit"):
        rate_to_price_per_sqft(100, "kanal")
