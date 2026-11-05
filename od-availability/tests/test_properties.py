from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from od_availability import Leg, is_open, net_contribution

money = st.decimals(min_value=0, max_value=5000, places=2)
legs = st.lists(
    st.builds(Leg, bid_price=money, seats_left=st.integers(min_value=0, max_value=9)),
    min_size=1,
    max_size=3,
)


@given(fare_value=money, legs=legs)
def test_class_is_open_exactly_with_seats_on_every_leg_and_positive_net_contribution(
    fare_value: Decimal, legs: list[Leg]
):
    has_seats = all(leg.seats_left > 0 for leg in legs)
    assert is_open(fare_value, legs) == (has_seats and net_contribution(fare_value, legs) > 0)


@given(fare_value=money, legs=legs, extra_leg=st.builds(Leg, money, st.integers(0, 9)))
def test_adding_a_leg_never_raises_net_contribution(
    fare_value: Decimal, legs: list[Leg], extra_leg: Leg
):
    assert net_contribution(fare_value, [*legs, extra_leg]) <= net_contribution(fare_value, legs)


@given(fare_value=money, legs=legs)
def test_leg_order_does_not_matter(fare_value: Decimal, legs: list[Leg]):
    assert net_contribution(fare_value, legs) == net_contribution(fare_value, legs[::-1])
    assert is_open(fare_value, legs) == is_open(fare_value, legs[::-1])
