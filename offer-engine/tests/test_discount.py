from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from offer_engine import discount_percent, discounted_price

scenarios("dynamic_discount.feature")


@given(
    parsers.parse("a maximum discount of {max_percent} percent and a constant of {constant}"),
    target_fixture="curve",
)
def _curve(max_percent: str, constant: str) -> tuple[Decimal, Decimal]:
    return Decimal(max_percent), Decimal(constant)


@when(parsers.parse("the customer spends {spend}"), target_fixture="spend")
def _spend(spend: str) -> Decimal:
    return Decimal(spend)


@when(
    parsers.parse("the customer spends {spend} on a bundle priced {price}"),
    target_fixture="result",
)
def _spend_on_bundle(curve: tuple[Decimal, Decimal], spend: str, price: str) -> Decimal:
    percent = discount_percent(Decimal(spend), *curve)
    return discounted_price(Decimal(price), percent)


@then(parsers.parse("the discount is {expected} percent"))
def _discount(curve: tuple[Decimal, Decimal], spend: Decimal, expected: str) -> None:
    assert discount_percent(spend, *curve) == Decimal(expected)


@then(parsers.parse("the price offered is {expected}"))
def _price(result: Decimal, expected: str) -> None:
    assert result == Decimal(expected)


@then("the request is invalid")
def _invalid(curve: tuple[Decimal, Decimal], spend: Decimal) -> None:
    with pytest.raises(ValueError):
        discount_percent(spend, *curve)


@pytest.mark.parametrize(("price", "percent"), [("-1", "5"), ("100", "-1"), ("100", "101")])
def test_a_discounted_price_needs_a_price_and_a_percent_in_range(price: str, percent: str):
    with pytest.raises(ValueError):
        discounted_price(Decimal(price), Decimal(percent))
