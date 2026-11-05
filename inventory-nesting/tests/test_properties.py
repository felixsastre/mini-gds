from hypothesis import given
from hypothesis import strategies as st

from inventory_nesting import Inventory, Nesting, SaleRejectedError, availability_shown

CLASSES = ("Y", "B", "M")
seats = st.integers(min_value=0, max_value=500)
authorizations = st.fixed_dictionaries(dict.fromkeys(CLASSES, seats))
bookings = st.fixed_dictionaries(dict.fromkeys(CLASSES, seats))


def inventory_with(auths: dict[str, int], sold: dict[str, int]) -> Inventory:
    inventory = Inventory({name: auths[name] for name in CLASSES})  # order = hierarchy
    inventory.load_bookings(sold)
    return inventory


@given(computed=st.integers(-1000, 1000), cap=st.sampled_from([7, 9]))
def test_shown_availability_stays_between_zero_and_cap(computed: int, cap: int) -> None:
    assert 0 <= availability_shown(computed, cap) <= cap


@given(
    auths=authorizations,
    sold=bookings,
    requested=seats,
    nesting=st.sampled_from(Nesting),
    booking_class=st.sampled_from(CLASSES),
)
def test_a_sale_books_exactly_the_requested_seats_in_that_class_or_nothing(
    auths: dict[str, int],
    sold: dict[str, int],
    requested: int,
    nesting: Nesting,
    booking_class: str,
) -> None:
    inventory = inventory_with(auths, sold)
    before = inventory.availability(booking_class, nesting)
    try:
        inventory.sell(booking_class, requested, nesting)
    except SaleRejectedError:
        assert requested > before
        expected = sold
    else:
        assert requested <= before
        expected = {**sold, booking_class: sold[booking_class] + requested}

    reference = inventory_with(auths, expected)
    assert inventory.total_sold == reference.total_sold
    for name in CLASSES:
        for mode in Nesting:
            assert inventory.availability(name, mode) == reference.availability(name, mode)


@given(auths=authorizations, sold=bookings)
def test_net_availability_never_grows_down_the_hierarchy(
    auths: dict[str, int], sold: dict[str, int]
) -> None:
    inventory = inventory_with(auths, sold)
    net = [inventory.availability(name, Nesting.NET) for name in CLASSES]
    assert net == sorted(net, reverse=True)


@given(auths=authorizations, sold=bookings, booking_class=st.sampled_from(CLASSES))
def test_net_availability_is_the_smallest_margin_from_the_class_up(
    auths: dict[str, int], sold: dict[str, int], booking_class: str
) -> None:
    """Each class's margin is its authorization minus what is sold in it and the classes below."""
    inventory = inventory_with(auths, sold)
    position = CLASSES.index(booking_class)
    margins = [
        auths[name] - sum(sold[lower] for lower in CLASSES[index:])
        for index, name in enumerate(CLASSES)
    ]
    assert inventory.availability(booking_class, Nesting.NET) == min(margins[: position + 1])
