from decimal import Decimal

import pytest

from app.modules.trip.budget import InvalidBudgetAmount, convert_budget_to_irr


@pytest.mark.parametrize(
    ("amount", "unit", "expected"),
    [
        ("20", "toman", Decimal("200")),
        ("20.1250", "toman", Decimal("201.2500")),
        ("20.1250", "rial", Decimal("20.1250")),
        (0, "rial", Decimal("0")),
    ],
)
def test_budget_comparison_conversion_is_exact(amount, unit, expected):
    assert convert_budget_to_irr(amount, unit) == expected


@pytest.mark.parametrize(
    ("amount", "unit"),
    [
        ("20", "IRR"),
        ("-1", "rial"),
        ("1.00001", "rial"),
        ("not-a-number", "toman"),
        ("NaN", "rial"),
        ("Infinity", "toman"),
        ("1000000000000000", "toman"),
    ],
)
def test_budget_conversion_rejects_unknown_or_unrepresentable_values(amount, unit):
    with pytest.raises(InvalidBudgetAmount):
        convert_budget_to_irr(amount, unit)
