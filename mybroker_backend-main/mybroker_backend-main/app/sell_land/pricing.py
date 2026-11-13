"""Pure Decimal-based land pricing conversions."""

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from app.sell_land.constants import AreaUnit


SQFT_PER_UNIT: dict[AreaUnit, Decimal] = {
    AreaUnit.SQFT: Decimal("1"),
    AreaUnit.SQM: Decimal("10.7639104167"),
    AreaUnit.DECIMAL: Decimal("435.6"),
    AreaUnit.ACRE: Decimal("43560"),
    AreaUnit.HECTARE: Decimal("107639.104167"),
}

# Keep recurring normalized rates much more precise than the process default.
# Decimal division is context-limited; doing this in a local context avoids
# changing the arithmetic policy for unrelated application code.
_PRICING_PRECISION = 60

PRICE_LABELS: dict[AreaUnit, str] = {
    AreaUnit.SQFT: "Price per Sq.ft",
    AreaUnit.SQM: "Price per Sq.m",
    AreaUnit.DECIMAL: "Price per Decimal",
    AreaUnit.ACRE: "Price per Acre",
    AreaUnit.HECTARE: "Price per Hectare",
}


def _unit(unit: AreaUnit | str) -> AreaUnit:
    try:
        parsed = unit if isinstance(unit, AreaUnit) else AreaUnit(unit)
    except (TypeError, ValueError):
        raise ValueError(f"Unsupported land area unit: {unit!r}") from None
    if parsed not in SQFT_PER_UNIT:
        raise ValueError(f"Unsupported land area unit for pricing conversion: {parsed.value!r}")
    return parsed


def _decimal(value: Any, *, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{name} must be a valid decimal value") from None
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite decimal value")
    return result


def area_to_sqft(area: Any, unit: AreaUnit | str) -> Decimal:
    """Convert area in the selected unit to square feet without rounding."""
    parsed_unit = _unit(unit)
    return _decimal(area, name="area") * SQFT_PER_UNIT[parsed_unit]


def rate_to_price_per_sqft(rate: Any, unit: AreaUnit | str) -> Decimal:
    """Normalize a seller-entered selected-unit rate to price per Sq.ft."""
    parsed_unit = _unit(unit)
    with localcontext() as context:
        context.prec = _PRICING_PRECISION
        return _decimal(rate, name="rate") / SQFT_PER_UNIT[parsed_unit]


def calculate_total_price(area_sqft: Any, price_per_sqft: Any) -> Decimal:
    """Calculate land total from square-foot area and normalized rate."""
    with localcontext() as context:
        context.prec = _PRICING_PRECISION
        return _decimal(area_sqft, name="area_sqft") * _decimal(price_per_sqft, name="price_per_sqft")


def rate_from_price_per_sqft(price_per_sqft: Any, unit: AreaUnit | str) -> Decimal:
    """Convert a normalized rate back to the selected-unit display rate."""
    parsed_unit = _unit(unit)
    return _decimal(price_per_sqft, name="price_per_sqft") * SQFT_PER_UNIT[parsed_unit]


def price_label(unit: AreaUnit | str) -> str:
    """Return the dynamic buyer-facing label for a supported pricing unit."""
    return PRICE_LABELS[_unit(unit)]
