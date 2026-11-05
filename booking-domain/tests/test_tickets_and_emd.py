import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from booking_domain import Booking, Emd, Segment, Status, Ticket, TicketNumber, issue_tickets

scenarios("tickets_and_emd.feature")


def comma_separated(text: str) -> list[str]:
    return [item.strip() for item in text.split(",")]


@given(parsers.parse("an itinerary with {coupons:d} flight coupons"), target_fixture="coupons")
def _itinerary(coupons: int) -> int:
    return coupons


@when(
    parsers.parse('tickets are issued starting at number "{number}"'),
    target_fixture="issued",
)
def _issue_tickets(coupons: int, number: str) -> list[Ticket] | ValueError:
    try:
        return issue_tickets(TicketNumber.parse(number), coupons)
    except ValueError as error:
        return error


@then(parsers.parse("{count:d} tickets are issued"))
def _count(issued: list[Ticket], count: int) -> None:
    assert len(issued) == count


@then(parsers.parse("the coupons per ticket are {split}"))
def _split(issued: list[Ticket], split: str) -> None:
    assert [ticket.coupons for ticket in issued] == [int(n) for n in comma_separated(split)]


@then(parsers.parse("the ticket numbers are {numbers}"))
def _numbers(issued: list[Ticket], numbers: str) -> None:
    assert [str(ticket.number) for ticket in issued] == comma_separated(numbers)


def _booking() -> Booking:
    return Booking("ABC123", ("Passenger",), (Segment("AA", "AA", Status.CONFIRMED),))


@given(parsers.parse('a booking with a ticket "{number}"'), target_fixture="booking")
def _booking_with_ticket(number: str) -> Booking:
    booking = _booking()
    booking.issue_ticket("Passenger", number)
    return booking


@given("a booking with no tickets", target_fixture="booking")
def _booking_without_tickets() -> Booking:
    return _booking()


def _issue_emd(booking: Booking, kind: str, ticket_number: str | None) -> Emd | ValueError:
    try:
        return booking.issue_emd(kind, ticket_number)
    except ValueError as error:
        return error


@when("an EMD of type A is issued for that ticket", target_fixture="issued")
def _emd_a(booking: Booking) -> Emd | ValueError:
    return _issue_emd(booking, "A", str(booking.tickets[0].number))


@when("an EMD of type A is issued without a ticket", target_fixture="issued")
def _emd_a_without_ticket(booking: Booking) -> Emd | ValueError:
    return _issue_emd(booking, "A", None)


@when(parsers.parse('an EMD of type A is issued for ticket "{number}"'), target_fixture="issued")
def _emd_a_for_ticket(booking: Booking, number: str) -> Emd | ValueError:
    return _issue_emd(booking, "A", number)


@when("an EMD of type B is issued", target_fixture="issued")
def _emd_b(booking: Booking) -> Emd | ValueError:
    return _issue_emd(booking, "B", None)


@when(parsers.parse('an EMD of type B is issued for ticket "{number}"'), target_fixture="issued")
def _emd_b_for_ticket(booking: Booking, number: str) -> Emd | ValueError:
    return _issue_emd(booking, "B", number)


@then(parsers.parse('the EMD is associated with ticket "{number}"'))
def _emd_ticket(issued: Emd, number: str) -> None:
    assert issued.ticket is not None
    assert str(issued.ticket) == number


@then("the EMD has no associated ticket")
def _emd_standalone(issued: Emd) -> None:
    assert issued.ticket is None


@then("the issue is rejected")
def _rejected(issued: object) -> None:
    assert isinstance(issued, ValueError)


NUMBER = TicketNumber("125", "1234567890")


@pytest.mark.parametrize(
    ("kind", "ticket"), [("A", None), ("B", NUMBER), ("Z", None), ("a", NUMBER), ("", None)]
)
def test_an_emd_checks_its_own_type_and_ticket(kind: str, ticket: TicketNumber | None) -> None:
    with pytest.raises(ValueError):
        Emd(kind, ticket)


@pytest.mark.parametrize(("kind", "ticket"), [("A", NUMBER), ("B", None)])
def test_a_valid_emd_is_accepted(kind: str, ticket: TicketNumber | None) -> None:
    assert Emd(kind, ticket).kind == kind


@pytest.mark.parametrize("coupons", [0, -1, 5, 12])
def test_a_ticket_holds_one_to_four_coupons(coupons: int) -> None:
    with pytest.raises(ValueError):
        Ticket(NUMBER, coupons)
