from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from offer_engine import (
    Arm,
    Bundle,
    Segment,
    build_offers,
    cumulative_regret,
    discount_percent,
    discounted_price,
    segment_trip,
    ucb,
    update,
)

spend = st.decimals(min_value=0, max_value=10_000_000, places=2)


@given(
    days_ahead=st.integers(0, 400),
    stay_days=st.none() | st.integers(0, 60),
    travelers=st.integers(1, 9),
)
def test_every_trip_gets_exactly_one_segment(days_ahead, stay_days, travelers):
    segment = segment_trip(days_ahead, stay_days, travelers)
    assert isinstance(segment, Segment)
    assert (segment is Segment.ONE_WAY) == (stay_days is None)


@given(a=spend, b=spend)
def test_discount_never_falls_as_spend_grows(a: Decimal, b: Decimal):
    low, high = sorted((a, b))
    assert discount_percent(low, Decimal(10), Decimal(100)) <= discount_percent(
        high, Decimal(10), Decimal(100)
    )


@given(spend=spend)
def test_discount_stays_from_zero_up_to_below_the_maximum(spend: Decimal):
    assert Decimal(0) <= discount_percent(spend, Decimal(10), Decimal(100)) < Decimal(10)


@given(price=st.decimals(min_value=1, max_value=5000, places=2), spend=spend)
def test_discounted_price_never_exceeds_the_price(price: Decimal, spend: Decimal):
    percent = discount_percent(spend, Decimal(10), Decimal(100))
    assert discounted_price(price, percent) <= price


bundle = st.builds(
    Bundle,
    name=st.uuids().map(str),
    price=st.decimals(min_value=50, max_value=500, places=0),
    ancillaries=st.integers(0, 5),
    likelihood=st.fixed_dictionaries({"s": st.decimals(min_value=0, max_value=1, places=2)}),
    overall=st.decimals(min_value=0, max_value=1, places=2),
)


@given(bundles=st.lists(bundle, min_size=1, max_size=8))
def test_offers_never_repeat_a_bundle_and_best_has_the_top_likelihood(bundles: list[Bundle]):
    offers = build_offers(bundles, "s")
    shown = [b for b in (offers.best, offers.decoy, offers.popular) if b is not None]
    assert len(shown) == len({b.name for b in shown})
    assert offers.best.likelihood["s"] == max(b.likelihood["s"] for b in bundles)


@given(
    arms=st.lists(
        st.builds(Arm, name=st.uuids().map(str), pulls=st.integers(0, 50), mean=st.floats(0, 1)),
        min_size=1,
        max_size=5,
    )
)
def test_ucb_never_skips_an_untried_arm(arms: list[Arm]):
    if any(arm.pulls == 0 for arm in arms):
        assert ucb(arms).pulls == 0


@given(
    arm=st.builds(Arm, name=st.just("A"), pulls=st.integers(0, 50), mean=st.floats(0, 1)),
    reward=st.sampled_from([0.0, 1.0]),
)
def test_update_keeps_the_mean_between_zero_and_one(arm: Arm, reward: float):
    updated = update(arm, reward)
    assert updated.pulls == arm.pulls + 1
    assert -1e-9 <= updated.mean <= 1 + 1e-9


@given(
    means=st.dictionaries(st.sampled_from("ABC"), st.floats(0, 1), min_size=1),
    data=st.data(),
)
def test_regret_is_never_negative(means: dict[str, float], data):
    chosen = data.draw(st.lists(st.sampled_from(sorted(means)), max_size=20))
    assert cumulative_regret(means, chosen) >= 0
