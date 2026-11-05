"""Runs features/search.feature against the running system (`scripts/dev.sh`)."""

import httpx2 as httpx
from pytest_bdd import given, parsers, scenarios, then

from tests.e2e.system import API, CACHE, HOST, ok, set_seats

scenarios("search.feature")


@given(
    parsers.parse(
        "the airline sells these bundles on flight {flight} from {origin} to {destination}:"
    ),
    target_fixture="world",
)
def _catalog(datatable: list[list[str]], flight: str, origin: str, destination: str) -> dict:
    header, *rows = datatable
    segments = header[4:-1]
    bundles = [
        {
            "name": row[0],
            "booking_class": row[1],
            "price": row[2],
            "ancillaries": int(row[3]),
            "likelihood": dict(zip(segments, row[4:-1], strict=True)),
            "overall": row[-1],
        }
        for row in rows
    ]
    catalog = {"flight": flight, "origin": origin, "destination": destination, "bundles": bundles}
    ok(httpx.put(f"{API}/admin/catalog", json=catalog))
    return {"flight": flight}


@given(
    parsers.re(
        r"class (?P<first>\w+) has (?P<first_seats>\d+) seats? and class (?P<second>\w+) has "
        r"(?P<second_seats>\d+) seats?(?: at the airline)? on flight (?P<flight>\w+)"
    )
)
def _seats(first: str, first_seats: str, second: str, second_seats: str, flight: str) -> None:
    for booking_class, seats in ((first, first_seats), (second, second_seats)):
        set_seats(flight, booking_class, int(seats))


@given(parsers.parse("the distributor was never told that class {booking_class} closed"))
def _never_told(world: dict, booking_class: str) -> None:
    # The distributor still holds the copy it had while the class was open.
    update = {"flight": world["flight"], "class": booking_class, "seats": 1}
    ok(httpx.post(f"{CACHE}/updates", json=update))


@given(parsers.parse("the distributor has no copy of class {booking_class}"))
def _no_copy(booking_class: str) -> None:
    # The cache keeps no copy per class: dropping all of them leaves none for this one.
    ok(httpx.post(f"{CACHE}/admin/reset"))


@given(parsers.parse("the airline cannot answer about class {booking_class}"))
def _outage(world: dict, booking_class: str) -> None:
    ok(httpx.put(f"{HOST}/admin/flights/{world['flight']}/classes/{booking_class}/outage"))


def offer_for(world: dict, role: str) -> dict | None:
    return next((o for o in world["result"]["offers"] if o["role"] == role), None)


@then(parsers.parse("the best offer is {bundle} at {price}"))
def _best(world: dict, bundle: str, price: str) -> None:
    offer = offer_for(world, "best")
    assert offer is not None
    assert (offer["bundle"], offer["price"]) == (bundle, price)


@then(parsers.parse("the popular offer is {bundle} at {price}"))
def _popular(world: dict, bundle: str, price: str) -> None:
    offer = offer_for(world, "popular")
    assert offer is not None
    assert (offer["bundle"], offer["price"]) == (bundle, price)


@then(parsers.parse("the search report shows {count:d} open-wrong error caught"))
def _report(world: dict, count: int) -> None:
    assert world["result"]["open_wrong_caught"] == count


@then(
    parsers.parse(
        "the search report shows {count:d} class left out because the airline did not answer"
    )
)
def _left_out(world: dict, count: int) -> None:
    assert world["result"]["host_unavailable"] == count
