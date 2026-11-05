"""Runs features/connection_search.feature against the running system (`scripts/dev.sh`)."""

import httpx2 as httpx
from pytest_bdd import given, parsers, scenarios, then

from tests.e2e.system import API, HOST, ok

scenarios("connection_search.feature")


@given(
    parsers.parse(
        "the airline sells these bundles from {origin} to {destination} "
        "on flights {first} and {second}:"
    )
)
def _catalog(
    world: dict, datatable: list[list[str]], origin: str, destination: str, first: str, second: str
) -> None:
    world["itinerary"] = f"{first}+{second}"
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
    catalog = {
        "flight": world["itinerary"],
        "origin": origin,
        "destination": destination,
        "bundles": bundles,
    }
    ok(httpx.put(f"{API}/admin/catalog", json=catalog))


@given(
    parsers.re(
        r"the airline values class (?P<first>\w+) at (?P<first_value>\d+) and class "
        r"(?P<second>\w+) at (?P<second_value>\d+) from \w+ to \w+"
    )
)
def _values(world: dict, first: str, first_value: str, second: str, second_value: str) -> None:
    for booking_class, value in ((first, first_value), (second, second_value)):
        url = f"{HOST}/admin/itineraries/{world['itinerary']}/classes/{booking_class}/value"
        ok(httpx.put(url, json={"value": value}))


@given(parsers.parse("the bid price is {bid_price:d} on {flight}"))
def _bid_price(bid_price: int, flight: str) -> None:
    ok(httpx.put(f"{HOST}/admin/flights/{flight}/bid-price", json={"bid_price": str(bid_price)}))


@then(
    parsers.re(
        r"(?P<first>\w+) is (?P<first_state>offered|not offered) and "
        r"(?P<second>\w+) is (?P<second_state>offered|not offered)"
    )
)
def _offered(world: dict, first: str, first_state: str, second: str, second_state: str) -> None:
    offered = {offer["bundle"] for offer in world["result"]["offers"]}
    assert (first in offered) == (first_state == "offered"), offered
    assert (second in offered) == (second_state == "offered"), offered
