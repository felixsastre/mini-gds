"""Steps shared by the end-to-end features."""

import re
import time

import httpx2 as httpx
import pytest
from pytest_bdd import given, parsers, then, when

from tests.e2e.system import (
    API,
    HOST,
    SECONDS_PER_MINUTE,
    eventually,
    ok,
    reset_system,
    set_seats,
)

MARGIN = 0.5  # seconds: lets the system settle after a deadline


@pytest.fixture(autouse=True)
def clean_system() -> None:
    reset_system()


@pytest.fixture
def world() -> dict:
    return {}


def reserve(flights: list[str], booking_class: str) -> httpx.Response:
    body = {"flights": flights, "booking_class": booking_class}
    return httpx.post(f"{API}/reservations", json=body)


def booking(world: dict) -> dict:
    return ok(httpx.get(f"{API}/reservations/{world['id']}")).json()


def host_seats(flight: str, booking_class: str) -> int:
    return ok(httpx.get(f"{HOST}/flights/{flight}/classes/{booking_class}/seats")).json()["seats"]


def assert_equal(actual: object, expected: object) -> None:
    assert actual == expected, f"{actual!r} != {expected!r}"


# --- the airline ---


@given(
    parsers.re(
        r"class (?P<booking_class>\w+) has (?P<seats>\d+) seats? at the airline "
        r"on flight (?P<flight>\w+)"
    )
)
def _class_seats(booking_class: str, seats: str, flight: str) -> None:
    set_seats(flight, booking_class, int(seats))


@given(
    parsers.re(
        r"classes (?P<first>\w+) and (?P<second>\w+) have (?P<seats>\d+) seats at the airline "
        r"on flights (?P<flight_a>\w+) and (?P<flight_b>\w+)"
    )
)
def _classes_seats(first: str, second: str, seats: str, flight_a: str, flight_b: str) -> None:
    for flight in (flight_a, flight_b):
        for booking_class in (first, second):
            set_seats(flight, booking_class, int(seats))


@then(parsers.parse("class {booking_class} on flight {flight} has {seats:d} seats at the airline"))
def _host_seats(booking_class: str, flight: str, seats: int) -> None:
    eventually(lambda: assert_equal(host_seats(flight, booking_class), seats))


# --- search ---


@when(
    parsers.re(
        r"a customer searches (?P<origin>\w+) to (?P<destination>\w+), (?P<travelers>\d+) "
        r"travelers?, booked (?P<days_ahead>\d+) days ahead, staying (?P<stay_days>\d+) days?"
    )
)
def _search(
    world: dict, origin: str, destination: str, travelers: str, days_ahead: str, stay_days: str
) -> None:
    request = {
        "origin": origin,
        "destination": destination,
        "travelers": int(travelers),
        "days_ahead": int(days_ahead),
        "stay_days": int(stay_days),
    }
    world["result"] = ok(httpx.post(f"{API}/search", json=request)).json()


@then(parsers.parse("the offers are {bundle} only"))
def _only(world: dict, bundle: str) -> None:
    assert [o["bundle"] for o in world["result"]["offers"]] == [bundle]


# --- reservation ---


@given(parsers.parse("a customer reserved class {booking_class} on flight {flight}"))
@when(parsers.parse("a customer reserves class {booking_class} on flight {flight}"))
def _reserve(world: dict, booking_class: str, flight: str) -> None:
    _store_reservation(world, reserve([flight], booking_class))


FLIGHT_LIST = r"\w+(?:, \w+)* and \w+"  # "AA100 and AA200", "AA100, AA200 and AA300"


def flight_numbers(text: str) -> list[str]:
    return [word for word in re.findall(r"\w+", text) if word != "and"]


@given(
    parsers.re(
        rf"a customer reserved class (?P<booking_class>\w+) "
        rf"on the connection of flights (?P<flights>{FLIGHT_LIST})"
    )
)
@when(
    parsers.re(
        rf"a customer reserves class (?P<booking_class>\w+) "
        rf"on the connection of flights (?P<flights>{FLIGHT_LIST})"
    )
)
def _reserve_connection(world: dict, booking_class: str, flights: str) -> None:
    _store_reservation(world, reserve(flight_numbers(flights), booking_class))


@given(
    parsers.re(
        rf"class (?P<booking_class>\w+) has (?P<seats>\d+) seats at the airline "
        rf"on each of flights (?P<flights>{FLIGHT_LIST})"
    )
)
def _class_seats_on_each(booking_class: str, seats: str, flights: str) -> None:
    for flight in flight_numbers(flights):
        set_seats(flight, booking_class, int(seats))


def _store_reservation(world: dict, response: httpx.Response) -> None:
    world["response"] = response
    if response.status_code == 201:
        world["id"] = response.json()["id"]


@when(parsers.parse("{minutes:d} minutes pass"))
def _pass(minutes: int) -> None:
    time.sleep(minutes * SECONDS_PER_MINUTE + MARGIN)


@when("the customer pays")
def _pay(world: dict) -> None:
    world["payment"] = ok(httpx.post(f"{API}/reservations/{world['id']}/payment", json={}))


@when("the customer pays and the payment is declined")
def _pay_declined(world: dict) -> None:
    body = {"decline": True}
    world["payment"] = ok(httpx.post(f"{API}/reservations/{world['id']}/payment", json=body))


@then("the booking has a GDS locator and no ticket")
def _locator_no_ticket(world: dict) -> None:
    view = booking(world)
    assert view["gds_locator"]
    assert view["ticket"] is None


@then(parsers.parse("the segment status is {code}"))
def _status(world: dict, code: str) -> None:
    def check() -> None:
        statuses = booking(world)["segment_statuses"]
        assert statuses and set(statuses) == {code}, statuses

    eventually(check)


@then(parsers.parse("the booking has {count:d} segments with status {code}"))
def _segments(world: dict, count: int, code: str) -> None:
    eventually(lambda: assert_equal(booking(world)["segment_statuses"], [code] * count))


@then(parsers.parse("the booking has a ticket of {digits:d} digits"))
def _ticket(world: dict, digits: int) -> None:
    ticket = booking(world)["ticket"]
    assert re.fullmatch(rf"\d{{3}}-\d{{{digits - 3}}}", ticket), ticket


@then(parsers.parse("the booking has {count:d} tickets with consecutive numbers"))
def _consecutive_tickets(world: dict, count: int) -> None:
    view = booking(world)
    tickets = view["tickets"]
    assert len(tickets) == count, tickets
    assert view["ticket"] == tickets[0], view
    documents = [int(ticket.split("-")[1]) for ticket in tickets]
    assert documents == list(range(documents[0], documents[0] + count)), tickets
    assert len({ticket.split("-")[0] for ticket in tickets}) == 1, tickets


@then("the booking has no ticket")
def _no_ticket(world: dict) -> None:
    assert booking(world)["ticket"] is None


@then("the airline cannot confirm the seat")
def _cannot_confirm(world: dict) -> None:
    assert world["response"].status_code == 409
    assert world["response"].json()["segment_statuses"] == ["UC"]


@then("no booking is created")
def _no_booking(world: dict) -> None:
    assert world["response"].json()["gds_locator"] is None
    assert "id" not in world["response"].json()
