from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from offer_engine import Bundle, Segment

from mini_gds.api import create_app
from mini_gds.cache_client import CacheUnavailableError, HostUnavailableError
from mini_gds.search import Listing, search

CATALOG = {
    "flight": "AA100",
    "origin": "JFK",
    "destination": "LHR",
    "bundles": [
        {
            "name": "Basic",
            "booking_class": "K",
            "price": "200",
            "ancillaries": 0,
            "likelihood": {"business": "0.30", "leisure": "0.80"},
            "overall": "0.60",
        },
        {
            "name": "Flex",
            "booking_class": "M",
            "price": "260",
            "ancillaries": 2,
            "likelihood": {"business": "0.70", "leisure": "0.20"},
            "overall": "0.40",
        },
    ],
}
BUSINESS_TRIP = {
    "origin": "JFK",
    "destination": "LHR",
    "travelers": 1,
    "days_ahead": 3,
    "stay_days": 1,
}


class FakeCache:
    """The distributor's copy (`copy`) can disagree with the airline (`airline`)."""

    def __init__(self, copy: dict[tuple[str, str], int], airline: dict[tuple[str, str], int]):
        self.copy, self.airline = copy, airline
        self.wash_top: int | None = None

    def seats(self, flight: str, booking_class: str) -> int:
        return self.copy[(flight, booking_class)]

    def wash(self, offers: list[tuple[str, str]], top: int) -> tuple[list[tuple[str, str]], int]:
        self.wash_top = top
        dropped = [key for key in offers[:top] if self.airline[key] == 0]
        return [key for key in offers if key not in dropped], len(dropped)


class UnansweredCache(FakeCache):
    """A distributor with no copy of class M, and an airline that cannot answer about it."""

    def seats(self, flight: str, booking_class: str) -> int:
        if booking_class == "M":
            raise HostUnavailableError
        return super().seats(flight, booking_class)


def client_with(cache: FakeCache, catalog: dict = CATALOG) -> TestClient:
    client = TestClient(create_app(cache, wash_top=2))
    assert client.put("/admin/catalog", json=catalog).status_code == 204
    return client


def seats(k: int, m: int) -> dict[tuple[str, str], int]:
    return {("AA100", "K"): k, ("AA100", "M"): m}


@pytest.fixture
def both_open() -> FakeCache:
    return FakeCache(copy=seats(9, 4), airline=seats(9, 4))


def test_a_business_trip_gets_flex_as_best_and_basic_as_popular(both_open: FakeCache) -> None:
    body = client_with(both_open).post("/search", json=BUSINESS_TRIP).json()
    assert body["segment"] == "business"
    assert body["offers"] == [
        {"role": "best", "bundle": "Flex", "booking_class": "M", "price": "260"},
        {"role": "popular", "bundle": "Basic", "booking_class": "K", "price": "200"},
    ]
    assert body["open_wrong_caught"] == 0


def test_a_closed_class_removes_its_bundle() -> None:
    cache = FakeCache(copy=seats(9, 0), airline=seats(9, 0))
    body = client_with(cache).post("/search", json=BUSINESS_TRIP).json()
    assert [offer["bundle"] for offer in body["offers"]] == ["Basic"]


def test_a_stale_open_class_is_washed_out_and_counted() -> None:
    cache = FakeCache(copy=seats(9, 4), airline=seats(9, 0))
    body = client_with(cache).post("/search", json=BUSINESS_TRIP).json()
    assert [offer["bundle"] for offer in body["offers"]] == ["Basic"]
    assert body["open_wrong_caught"] == 1
    assert cache.wash_top == 2


def test_no_open_class_gives_no_offers() -> None:
    cache = FakeCache(copy=seats(0, 0), airline=seats(0, 0))
    body = client_with(cache).post("/search", json=BUSINESS_TRIP).json()
    assert body["offers"] == []


def test_a_search_on_another_route_gives_no_offers(both_open: FakeCache) -> None:
    other = {**BUSINESS_TRIP, "destination": "MAD"}
    assert client_with(both_open).post("/search", json=other).json()["offers"] == []


def test_prices_are_exact_decimals(both_open: FakeCache) -> None:
    body = client_with(both_open).post("/search", json=BUSINESS_TRIP).json()
    assert Decimal(body["offers"][0]["price"]) == Decimal(260)


def test_listings_that_share_a_bundle_name_keep_their_own_class_and_price() -> None:
    flex_m = Bundle("Flex", Decimal(260), 2, {"business": Decimal("0.90")}, Decimal("0.40"))
    flex_y = Bundle("Flex", Decimal(300), 2, {"business": Decimal("0.10")}, Decimal("0.40"))
    listings = [Listing("AA100", "M", flex_m), Listing("AA200", "Y", flex_y)]
    open_everywhere = {("AA100", "M"): 4, ("AA200", "Y"): 4}

    result = search(listings, Segment.BUSINESS, FakeCache(open_everywhere, open_everywhere), 2)

    best = result.offers[0]
    assert (best.role, best.booking_class, best.price) == ("best", "M", "260")


def test_a_trip_type_without_data_is_offered_by_overall_sales() -> None:
    # Flex is listed first and the catalog says nothing about couples: the best bundle is
    # the one with the highest overall share, not the first one.
    catalog = {**CATALOG, "bundles": CATALOG["bundles"][::-1]}
    client = client_with(FakeCache(copy=seats(9, 4), airline=seats(9, 4)), catalog)
    couple = {**BUSINESS_TRIP, "travelers": 2, "days_ahead": 30, "stay_days": 7}

    body = client.post("/search", json=couple).json()

    assert body["segment"] == "couple"
    assert [(o["role"], o["bundle"]) for o in body["offers"]] == [
        ("best", "Basic"),
        ("popular", "Flex"),
    ]


def test_a_class_the_airline_cannot_answer_about_is_left_out_and_counted() -> None:
    cache = UnansweredCache(copy=seats(9, 4), airline=seats(9, 4))
    body = client_with(cache).post("/search", json=BUSINESS_TRIP).json()
    assert [offer["bundle"] for offer in body["offers"]] == ["Basic"]
    assert (body["open_wrong_caught"], body["host_unavailable"]) == (0, 1)


def test_a_search_with_every_class_answered_reports_no_unavailable_class(
    both_open: FakeCache,
) -> None:
    body = client_with(both_open).post("/search", json=BUSINESS_TRIP).json()
    assert body["host_unavailable"] == 0


def test_when_the_airline_cannot_answer_about_any_class_there_are_no_offers() -> None:
    class AllDown(FakeCache):
        def seats(self, flight: str, booking_class: str) -> int:
            raise HostUnavailableError

    body = client_with(AllDown(copy={}, airline={})).post("/search", json=BUSINESS_TRIP).json()
    assert (body["offers"], body["host_unavailable"]) == ([], 2)


@pytest.mark.parametrize("change", [{"travelers": 0}, {"days_ahead": -5}, {"stay_days": -1}])
def test_an_impossible_trip_is_a_validation_error_not_a_crash(
    both_open: FakeCache, change: dict
) -> None:
    response = client_with(both_open).post("/search", json={**BUSINESS_TRIP, **change})
    assert response.status_code == 422


def test_search_answers_503_when_the_availability_cache_is_down() -> None:
    class DownCache(FakeCache):
        def seats(self, flight: str, booking_class: str) -> int:
            raise CacheUnavailableError

    cache = DownCache(copy={}, airline={})
    assert client_with(cache).post("/search", json=BUSINESS_TRIP).status_code == 503
