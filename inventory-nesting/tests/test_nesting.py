from collections.abc import Callable

from pytest_bdd import given, parsers, scenarios, then, when

from inventory_nesting import Inventory, Nesting, SaleRejectedError, availability_shown

scenarios("nesting.feature", "availability_cap.feature")


def parse_bookings(text: str) -> dict[str, int]:
    return {name: int(seats) for name, seats in (item.split() for item in text.split(", "))}


@given(parsers.parse("a cabin with {seats:d} seats"), target_fixture="capacity")
def _cabin(seats: int) -> int:
    return seats


@given("the following authorizations, highest class first:", target_fixture="inventory")
def _authorizations(datatable: list[list[str]]) -> Inventory:
    rows = datatable[1:]  # first row is the header
    return Inventory({name: int(authorization) for name, authorization in rows})


@given(parsers.parse("bookings of {bookings}"))
def _bookings(inventory: Inventory, bookings: str) -> None:
    inventory.load_bookings(parse_bookings(bookings))


@given(parsers.parse("the airline uses {method} nesting"), target_fixture="nesting")
def _nesting(method: str) -> Nesting:
    return Nesting(method)


@given(parsers.parse("the distributor cap is {cap:d}"), target_fixture="cap")
def _cap(cap: int) -> int:
    return cap


@given(
    parsers.parse("a class has a computed availability of {computed:d}"),
    target_fixture="computed",
)
def _computed(computed: int) -> int:
    return computed


@when(parsers.parse("{seats:d} seats are sold in class {booking_class}"))
def _sell(inventory: Inventory, nesting: Nesting, seats: int, booking_class: str) -> None:
    inventory.sell(booking_class, seats, nesting)


def attempt(action: Callable[[], object]) -> str:
    """What came of an action: accepted, rejected for lack of seats, or invalid input."""
    try:
        action()
    except SaleRejectedError:
        return "rejected"
    except ValueError:
        return "invalid"
    return "accepted"


@when(
    parsers.parse("a seat is requested in class {booking_class}"),
    target_fixture="outcome",
)
def _request_seat(inventory: Inventory, nesting: Nesting, booking_class: str) -> str:
    return attempt(lambda: inventory.sell(booking_class, 1, nesting))


@when(
    parsers.parse("{seats:d} seats are requested in class {booking_class}"),
    target_fixture="outcome",
)
def _request_seats(inventory: Inventory, nesting: Nesting, seats: int, booking_class: str) -> str:
    return attempt(lambda: inventory.sell(booking_class, seats, nesting))


@when(parsers.parse("bookings of {bookings} are loaded"), target_fixture="outcome")
def _load_bookings(inventory: Inventory, bookings: str) -> str:
    return attempt(lambda: inventory.load_bookings(parse_bookings(bookings)))


@when(
    parsers.parse("a cabin is set up with an authorization of {seats:d} for class {booking_class}"),
    target_fixture="outcome",
)
def _set_up_cabin(seats: int, booking_class: str) -> str:
    return attempt(lambda: Inventory({booking_class: seats}))


@when("the availability is shown to the distributor", target_fixture="outcome")
def _show(computed: int, cap: int) -> str:
    return attempt(lambda: availability_shown(computed, cap))


@then(parsers.parse("availability of {booking_class} is {expected:d}"))
def _availability(
    inventory: Inventory, nesting: Nesting, booking_class: str, expected: int
) -> None:
    assert inventory.availability(booking_class, nesting) == expected


@then(parsers.re(r"class (?P<booking_class>\w+) is (?P<state>available|unavailable)"))
def _state(inventory: Inventory, nesting: Nesting, booking_class: str, state: str) -> None:
    assert inventory.is_available(booking_class, nesting) == (state == "available")


@then("more seats are sold than the cabin has")
def _overbooked(inventory: Inventory, capacity: int) -> None:
    assert inventory.total_sold > capacity


@then(parsers.parse("the availability shown to the distributor is {expected:d}"))
def _shown(computed: int, cap: int, expected: int) -> None:
    assert availability_shown(computed, cap) == expected


@then(parsers.parse("the sale is {expected}"))
def _sale_outcome(outcome: str, expected: str) -> None:
    assert outcome == expected


@then("the request is invalid")
def _invalid(outcome: str) -> None:
    assert outcome == "invalid"
