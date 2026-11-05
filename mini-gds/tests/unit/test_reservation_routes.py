import pytest
from fastapi.testclient import TestClient

from mini_gds.api import create_app
from mini_gds.reservations import (
    HoldClosedError,
    ReservationNotFoundError,
    ReservationsUnavailableError,
)
from mini_gds.workflows import BookingView

HELD = BookingView(["HK"], "ABC123", None)
TICKETED = BookingView(["HK"], "ABC123", "999-1234567890", ["999-1234567890", "999-1234567891"])
UNABLE = BookingView(["UC"], None, None)


class FakeCache:
    def seats(self, flight: str, booking_class: str) -> int:
        return 0

    def wash(self, offers, top):
        return offers, 0


class FakeReservations:
    def __init__(self, sale: BookingView = HELD, down: bool = False) -> None:
        self.sale = sale
        self.down = down
        self.paid: list[tuple[str, bool]] = []
        self.reserved: list[str] = []

    async def reserve(self, flights: list[str], booking_class: str, passenger: str):
        if self.down:
            raise ReservationsUnavailableError
        self.reserved = flights
        return "res-1", self.sale

    async def pay(self, reservation_id: str, decline: bool) -> BookingView:
        if self.down:
            raise ReservationsUnavailableError
        if reservation_id == "closed":
            raise HoldClosedError
        self.paid.append((reservation_id, decline))
        return TICKETED

    async def get(self, reservation_id: str) -> BookingView:
        if self.down:
            raise ReservationsUnavailableError
        if reservation_id == "unknown":
            raise ReservationNotFoundError
        return HELD


def client(reservations: FakeReservations) -> TestClient:
    return TestClient(create_app(FakeCache(), reservations=reservations))


RESERVE = {"flights": ["AA100", "AA200"], "booking_class": "M"}


def test_reserving_returns_the_booking_and_its_id() -> None:
    response = client(FakeReservations()).post("/reservations", json=RESERVE)
    assert response.status_code == 201
    assert response.json() == {
        "id": "res-1",
        "segment_statuses": ["HK"],
        "gds_locator": "ABC123",
        "ticket": None,
        "tickets": [],
    }


def test_a_seat_the_airline_cannot_confirm_creates_no_booking() -> None:
    response = client(FakeReservations(UNABLE)).post("/reservations", json=RESERVE)
    assert response.status_code == 409
    assert response.json() == {
        "segment_statuses": ["UC"],
        "gds_locator": None,
        "ticket": None,
        "tickets": [],
    }


def test_paying_returns_the_ticket() -> None:
    fake = FakeReservations()
    response = client(fake).post("/reservations/res-1/payment", json={"decline": True})
    assert response.status_code == 200
    assert response.json()["ticket"] == "999-1234567890"
    assert response.json()["tickets"] == ["999-1234567890", "999-1234567891"]
    assert fake.paid == [("res-1", True)]


def test_paying_defaults_to_an_approved_payment() -> None:
    fake = FakeReservations()
    client(fake).post("/reservations/res-1/payment", json={})
    assert fake.paid == [("res-1", False)]


def test_paying_after_the_hold_closed_is_a_conflict() -> None:
    response = client(FakeReservations()).post("/reservations/closed/payment", json={})
    assert response.status_code == 409


def test_reading_a_reservation() -> None:
    assert client(FakeReservations()).get("/reservations/res-1").json()["gds_locator"] == "ABC123"


def test_an_unknown_reservation_is_not_found() -> None:
    assert client(FakeReservations()).get("/reservations/unknown").status_code == 404


@pytest.mark.parametrize(
    ("method", "path"), [("post", "/reservations"), ("get", "/reservations/x")]
)
def test_reservations_are_off_when_no_service_is_configured(method: str, path: str) -> None:
    app_client = TestClient(create_app(FakeCache()))
    response = getattr(app_client, method)(path, **({"json": RESERVE} if method == "post" else {}))
    assert response.status_code == 503


def test_every_flight_of_a_connection_reaches_the_service() -> None:
    fake = FakeReservations()
    client(fake).post("/reservations", json=RESERVE)
    assert fake.reserved == ["AA100", "AA200"]


def test_a_reservation_needs_at_least_one_flight() -> None:
    fake = FakeReservations()
    response = client(fake).post("/reservations", json={**RESERVE, "flights": []})
    assert response.status_code == 422
    assert fake.reserved == []


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/reservations"),
        ("post", "/reservations/res-1/payment"),
        ("get", "/reservations/res-1"),
    ],
)
def test_reservations_are_unavailable_when_temporal_does_not_answer(method: str, path: str) -> None:
    app_client = client(FakeReservations(down=True))
    response = getattr(app_client, method)(path, **({"json": RESERVE} if method == "post" else {}))
    assert response.status_code == 503


def test_a_reservation_of_more_than_twelve_flights_is_rejected() -> None:
    flights = [f"AA{number}" for number in range(100, 113)]
    response = client(FakeReservations()).post(
        "/reservations", json={**RESERVE, "flights": flights}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("flights", [["aa100"], ["A"], ["AA"], ["AA100 "], ["AA100+AA200"]])
def test_a_flight_that_is_not_a_flight_number_is_rejected(flights: list[str]) -> None:
    response = client(FakeReservations()).post(
        "/reservations", json={**RESERVE, "flights": flights}
    )
    assert response.status_code == 422


def test_a_reservation_needs_a_passenger_name() -> None:
    response = client(FakeReservations()).post("/reservations", json={**RESERVE, "passenger": ""})
    assert response.status_code == 422


@pytest.mark.parametrize("booking_class", ["", "M/x?y", "mm", "m", "MM"])
def test_a_booking_class_that_is_not_one_capital_letter_is_rejected(booking_class: str) -> None:
    response = client(FakeReservations()).post(
        "/reservations", json={**RESERVE, "booking_class": booking_class}
    )
    assert response.status_code == 422
