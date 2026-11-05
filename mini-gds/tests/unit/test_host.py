import pytest
from fastapi.testclient import TestClient

from mini_gds.host import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def set_seats(client: TestClient, flight: str, booking_class: str, seats: int) -> None:
    response = client.put(
        f"/admin/flights/{flight}/classes/{booking_class}/seats", json={"seats": seats}
    )
    assert response.status_code == 204


def seats(client: TestClient, flight: str, booking_class: str) -> int:
    return client.get(f"/flights/{flight}/classes/{booking_class}/seats").json()["seats"]


def test_a_class_reports_the_seats_it_was_given(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    set_seats(client, "AA100", "K", 7)
    assert (seats(client, "AA100", "M"), seats(client, "AA100", "K")) == (4, 7)


def test_availability_is_capped_at_nine(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 15)
    assert seats(client, "AA100", "M") == 9


def test_a_closed_class_reports_zero(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 0)
    assert seats(client, "AA100", "M") == 0


def test_an_unknown_class_is_not_found(client: TestClient) -> None:
    assert client.get("/flights/AA100/classes/M/seats").status_code == 404


def test_reset_forgets_every_flight(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    assert client.post("/admin/reset").status_code == 204
    assert client.get("/flights/AA100/classes/M/seats").status_code == 404


def sell(client: TestClient, flight: str, booking_class: str, sale_id: str) -> int:
    return client.post(
        f"/flights/{flight}/classes/{booking_class}/sales", json={"sale_id": sale_id}
    ).status_code


def test_a_sale_takes_one_seat(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    assert sell(client, "AA100", "M", "s1") == 201
    assert seats(client, "AA100", "M") == 3


def test_selling_the_same_sale_again_takes_no_second_seat(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    assert (sell(client, "AA100", "M", "s1"), sell(client, "AA100", "M", "s1")) == (201, 200)
    assert seats(client, "AA100", "M") == 3


def test_a_sale_id_cannot_be_reused_for_another_class(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    set_seats(client, "AA100", "K", 4)
    assert sell(client, "AA100", "M", "s1") == 201
    assert sell(client, "AA100", "K", "s1") == 409
    assert seats(client, "AA100", "M") == 3  # no second seat was taken


def test_a_sale_is_refused_when_the_class_is_closed(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 0)
    assert sell(client, "AA100", "M", "s1") == 409
    assert seats(client, "AA100", "M") == 0


def test_a_sale_is_refused_for_an_unknown_class(client: TestClient) -> None:
    assert sell(client, "AA100", "M", "s1") == 409


def test_releasing_a_sale_returns_the_seat_once(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    sell(client, "AA100", "M", "s1")
    for _ in range(2):
        assert client.delete("/flights/AA100/sales/s1").status_code == 204
    assert seats(client, "AA100", "M") == 4


def test_setting_seats_after_a_sale_still_shows_that_number(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    sell(client, "AA100", "M", "s1")
    set_seats(client, "AA100", "M", 4)
    assert seats(client, "AA100", "M") == 4


def test_concurrent_sales_never_oversell(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    set_seats(client, "AA100", "M", 1)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda n: sell(client, "AA100", "M", f"s{n}"), range(8)))
    assert sorted(results) == [201] + [409] * 7
    assert seats(client, "AA100", "M") == 0


def set_value(client: TestClient, itinerary: str, booking_class: str, value: int) -> None:
    response = client.put(
        f"/admin/itineraries/{itinerary}/classes/{booking_class}/value", json={"value": str(value)}
    )
    assert response.status_code == 204


def set_bid_price(client: TestClient, flight: str, bid_price: int) -> None:
    response = client.put(f"/admin/flights/{flight}/bid-price", json={"bid_price": str(bid_price)})
    assert response.status_code == 204


CONNECTION = "AA100+AA200"


def two_legs(client: TestClient, first: int = 4, second: int = 4) -> None:
    for booking_class in ("K", "M"):
        set_seats(client, "AA100", booking_class, first)
        set_seats(client, "AA200", booking_class, second)


def test_a_connection_without_a_value_is_judged_on_seats_alone(client: TestClient) -> None:
    two_legs(client, first=4, second=2)
    assert seats(client, CONNECTION, "M") == 2


def test_a_class_worth_more_than_its_legs_cost_is_open(client: TestClient) -> None:
    two_legs(client)
    set_value(client, CONNECTION, "K", 300)
    set_bid_price(client, "AA100", 100)
    set_bid_price(client, "AA200", 150)
    assert seats(client, CONNECTION, "K") == 4


@pytest.mark.parametrize(("second_bid", "shown"), [(199, 4), (200, 0), (220, 0)])
def test_a_class_is_open_only_while_the_net_contribution_is_above_zero(
    client: TestClient, second_bid: int, shown: int
) -> None:
    two_legs(client)
    set_value(client, CONNECTION, "K", 300)
    set_bid_price(client, "AA100", 100)
    set_bid_price(client, "AA200", second_bid)
    assert seats(client, CONNECTION, "K") == shown


def test_the_value_of_one_class_does_not_close_another(client: TestClient) -> None:
    two_legs(client)
    set_value(client, CONNECTION, "K", 300)
    set_value(client, CONNECTION, "M", 420)
    set_bid_price(client, "AA100", 100)
    set_bid_price(client, "AA200", 220)
    assert (seats(client, CONNECTION, "K"), seats(client, CONNECTION, "M")) == (0, 4)


def test_a_leg_without_seats_closes_a_valuable_class(client: TestClient) -> None:
    two_legs(client, first=4, second=0)
    set_value(client, CONNECTION, "M", 420)
    assert seats(client, CONNECTION, "M") == 0


def test_a_connection_with_an_unknown_leg_is_not_found(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    assert client.get("/flights/AA100+AA999/classes/M/seats").status_code == 404


def test_reset_forgets_values_and_bid_prices(client: TestClient) -> None:
    two_legs(client)
    set_value(client, CONNECTION, "K", 300)
    set_bid_price(client, "AA100", 500)
    client.post("/admin/reset")
    two_legs(client)
    assert seats(client, CONNECTION, "K") == 4


def test_a_negative_bid_price_is_refused(client: TestClient) -> None:
    response = client.put("/admin/flights/AA100/bid-price", json={"bid_price": "-1"})
    assert response.status_code == 422


def test_negative_seats_are_refused(client: TestClient) -> None:
    response = client.put("/admin/flights/AA100/classes/M/seats", json={"seats": -1})
    assert response.status_code == 422


def test_a_class_in_an_outage_does_not_answer_until_the_reset(client: TestClient) -> None:
    set_seats(client, "AA100", "M", 4)
    set_seats(client, "AA100", "K", 7)

    assert client.put("/admin/flights/AA100/classes/M/outage").status_code == 204

    assert client.get("/flights/AA100/classes/M/seats").status_code == 503
    assert seats(client, "AA100", "K") == 7  # only the class in the outage is affected
    client.post("/admin/reset")
    set_seats(client, "AA100", "M", 4)
    assert seats(client, "AA100", "M") == 4


def test_a_negative_market_value_is_a_validation_error_not_a_crash(client: TestClient) -> None:
    response = client.put("/admin/itineraries/AA100+AA200/classes/K/value", json={"value": "-1"})
    assert response.status_code == 422
