from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Leg:
    bid_price: Decimal
    seats_left: int

    def __post_init__(self) -> None:
        _check_money("bid price", self.bid_price)
        if not isinstance(self.seats_left, int) or isinstance(self.seats_left, bool):
            raise ValueError(f"seats left must be an integer, not {self.seats_left!r}")
        if self.seats_left < 0:
            raise ValueError(f"seats left cannot be negative: {self.seats_left}")


def _check_money(name: str, amount: Decimal) -> None:
    """Raise ValueError unless the amount is a finite, non-negative Decimal."""
    if not isinstance(amount, Decimal):
        raise ValueError(f"{name} must be a Decimal, not {type(amount).__name__}")
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{name} must be a finite amount that is not negative: {amount}")


def net_contribution(market_fare_value: Decimal, legs: Sequence[Leg]) -> Decimal:
    _check_money("market fare value", market_fare_value)
    return market_fare_value - sum((leg.bid_price for leg in legs), start=Decimal(0))


def is_open(market_fare_value: Decimal, legs: Sequence[Leg]) -> bool:
    _check_money("market fare value", market_fare_value)
    has_seats_on_every_leg = bool(legs) and all(leg.seats_left > 0 for leg in legs)
    return has_seats_on_every_leg and net_contribution(market_fare_value, legs) > 0
