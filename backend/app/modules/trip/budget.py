"""Exact Rial/Toman comparison conversion; persisted values keep original unit."""

from decimal import Decimal, InvalidOperation

MAX_IRR_NUMERIC_20_4 = Decimal("9999999999999999.9999")


class InvalidBudgetAmount(ValueError):
    """Budget cannot be represented exactly in the supported numeric range."""


def convert_budget_to_irr(amount: Decimal | int | str, unit: str) -> Decimal:
    """Return an exact Rial comparison amount without rounding.

    Callers must persist/display the original amount and unit separately. One
    Toman is exactly ten Rial; this helper never writes the converted value as
    the user's original budget.
    """
    try:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    except (InvalidOperation, TypeError):
        raise InvalidBudgetAmount from None
    if not value.is_finite() or value < 0 or value.as_tuple().exponent < -4:
        raise InvalidBudgetAmount
    if unit == "toman":
        converted = value * Decimal(10)
    elif unit == "rial":
        converted = value
    else:
        raise InvalidBudgetAmount
    if converted > MAX_IRR_NUMERIC_20_4 or converted.as_tuple().exponent < -4:
        raise InvalidBudgetAmount
    return converted
