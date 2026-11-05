from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from od_availability import Leg, is_open, net_contribution

scenarios("od_availability.feature")


def parse_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",")]


@given(parsers.parse("a market fare value of {value}"), target_fixture="fare_value")
def _fare_value(value: str) -> Decimal:
    return Decimal(value)


@given(parsers.parse("legs with bid prices {prices}"), target_fixture="bid_prices")
def _bid_prices(prices: str) -> list[Decimal]:
    return [Decimal(price) for price in parse_list(prices)]


@given(parsers.parse("seats left on those legs: {seats}"), target_fixture="legs")
def _legs(bid_prices: list[Decimal], seats: str) -> list[Leg]:
    seats_left = [int(count) for count in parse_list(seats)]
    return [Leg(price, count) for price, count in zip(bid_prices, seats_left, strict=True)]


@given("no legs", target_fixture="legs")
def _no_legs() -> list[Leg]:
    return []


@when(
    parsers.parse("a leg has a bid price of {price} and {seats:d} seats left"),
    target_fixture="rejection",
)
def _build_leg(price: str, seats: int) -> ValueError | None:
    try:
        Leg(Decimal(price), seats)
    except ValueError as error:
        return error
    return None


@then("the leg is rejected")
def _leg_rejected(rejection: ValueError | None) -> None:
    assert rejection is not None


@then(parsers.parse("the net contribution is {expected}"))
def _net_contribution(fare_value: Decimal, legs: list[Leg], expected: str) -> None:
    assert net_contribution(fare_value, legs) == Decimal(expected)


@then("the class cannot be evaluated")
def _cannot_be_evaluated(fare_value: Decimal, legs: list[Leg]) -> None:
    with pytest.raises(ValueError):
        is_open(fare_value, legs)
    with pytest.raises(ValueError):
        net_contribution(fare_value, legs)


@then(parsers.re(r"the class is (?P<status>open|closed)"))
def _status(fare_value: Decimal, legs: list[Leg], status: str) -> None:
    assert is_open(fare_value, legs) == (status == "open")


def test_a_bid_price_that_is_not_a_decimal_is_rejected() -> None:
    with pytest.raises(ValueError, match="Decimal"):
        Leg(300.5, 2)  # type: ignore[arg-type]


@pytest.mark.parametrize("fare_value", [600.0, 600, "600", None])
def test_a_market_fare_value_that_is_not_a_decimal_is_rejected(fare_value: object) -> None:
    legs = [Leg(Decimal(300), 2)]
    with pytest.raises(ValueError, match="Decimal"):
        is_open(fare_value, legs)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Decimal"):
        net_contribution(fare_value, legs)  # type: ignore[arg-type]


@pytest.mark.parametrize("seats_left", [2.0, True, "2", None])
def test_seats_left_must_be_an_integer(seats_left: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        Leg(Decimal(300), seats_left)  # type: ignore[arg-type]
