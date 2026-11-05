import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from booking_domain import Booking, Segment, Status, Ticket, TicketNumber

scenarios("booking.feature")


@given(
    parsers.re(
        r"a booking with (?P<passengers>\d+) passengers? and (?P<segments>\d+) segments?"
        r"(?:, (?P<cancelled>\d+) of them cancelled)?"
    ),
    converters={"passengers": int, "segments": int},
    target_fixture="booking",
)
def _booking(passengers: int, segments: int, cancelled: str | None) -> Booking:
    statuses = [Status.CANCELLED] * int(cancelled or 0)
    statuses += [Status.CONFIRMED] * (segments - len(statuses))
    return Booking(
        gds_locator="ABC123",
        passengers=tuple(f"Passenger {i + 1}" for i in range(passengers)),
        segments=tuple(Segment("AA", "AA", status) for status in statuses),
    )


@when(parsers.parse('the airline returns its locator "{locator}"'))
def _airline_locator(booking: Booking, locator: str) -> None:
    booking.receive_airline_locator(locator)


@when(
    parsers.re(
        r'a ticket is issued (?:for passenger (?P<position>\d+) )?with number "(?P<number>[^"]+)"'
    ),
    converters={"position": lambda text: int(text) if text else 1},
    target_fixture="outcome",
)
def _issue(booking: Booking, position: int, number: str) -> str:
    try:
        booking.issue_ticket(booking.passengers[position - 1], number)
    except ValueError:
        return "rejected"
    return "accepted"


@when(
    parsers.parse('conjunction tickets are issued starting at number "{number}"'),
    target_fixture="outcome",
)
def _issue_conjunction(booking: Booking, number: str) -> str:
    try:
        booking.issue_conjunction_tickets(booking.passengers[0], number)
    except ValueError:
        return "rejected"
    return "accepted"


@then("the booking has a GDS locator")
def _has_gds_locator(booking: Booking) -> None:
    assert booking.gds_locator


@then("the booking has no tickets")
def _no_tickets(booking: Booking) -> None:
    assert booking.tickets == []


@then(parsers.parse('the booking has the airline locator "{locator}"'))
def _has_airline_locator(booking: Booking, locator: str) -> None:
    assert booking.airline_locator == locator


@then(parsers.re(r"the booking has (?P<count>\d+) tickets?"), converters={"count": int})
def _ticket_count(booking: Booking, count: int) -> None:
    assert len(booking.tickets) == count


@then(parsers.parse('the ticket number is "{number}"'))
def _ticket_number(booking: Booking, number: str) -> None:
    assert str(booking.tickets[0].number) == number


@then(parsers.parse("the ticket has {coupons:d} coupons"))
def _coupons(booking: Booking, coupons: int) -> None:
    assert [ticket.coupons for ticket in booking.tickets] == [coupons]


@then(parsers.parse("the ticket numbers are {numbers}"))
def _ticket_numbers(booking: Booking, numbers: str) -> None:
    expected = [item.strip() for item in numbers.split(",")]
    assert [str(ticket.number) for ticket in booking.tickets] == expected


@then(parsers.re(r"the ticket is (?P<expected>accepted|rejected)"))
def _outcome(outcome: str, expected: str) -> None:
    assert outcome == expected


@pytest.mark.parametrize(
    ("passengers", "segments"),
    [(0, 1), (1, 0)],
)
def test_a_booking_needs_a_passenger_and_a_segment(passengers: int, segments: int) -> None:
    with pytest.raises(ValueError):
        Booking(
            gds_locator="ABC123",
            passengers=tuple("P" * passengers),
            segments=tuple(Segment("AA", "AA", Status.CONFIRMED) for _ in range(segments)),
        )


def test_a_booking_needs_a_gds_locator() -> None:
    with pytest.raises(ValueError):
        Booking("", ("P",), (Segment("AA", "AA", Status.CONFIRMED),))


def test_one_ticket_cannot_cover_more_than_four_segments() -> None:
    booking = Booking(
        "ABC123", ("P",), tuple(Segment("AA", "AA", Status.CONFIRMED) for _ in range(5))
    )
    with pytest.raises(ValueError):
        booking.issue_ticket("P", "125-1234567890")


def _booking_with_segments(count: int) -> Booking:
    segments = tuple(Segment("AA", "AA", Status.CONFIRMED) for _ in range(count))
    return Booking("ABC123", ("P",), segments)


def test_a_conjunction_that_reuses_a_number_issues_no_ticket() -> None:
    booking = _booking_with_segments(6)
    booking.tickets.append(Ticket(TicketNumber("125", "1234567891"), 1))
    with pytest.raises(ValueError):
        booking.issue_conjunction_tickets("P", "125-1234567890")
    assert len(booking.tickets) == 1


def test_a_conjunction_cannot_run_past_the_last_document_number() -> None:
    booking = _booking_with_segments(6)
    with pytest.raises(ValueError):
        booking.issue_conjunction_tickets("P", "125-9999999999")
    assert booking.tickets == []


def test_more_than_twelve_segments_cannot_be_ticketed() -> None:
    booking = _booking_with_segments(13)
    with pytest.raises(ValueError):
        booking.issue_conjunction_tickets("P", "125-1234567890")


def test_a_conjunction_ticket_carries_the_validating_carrier() -> None:
    booking = _booking_with_segments(5)
    tickets = booking.issue_conjunction_tickets("P", "125-1234567890", validating_carrier="IB")
    assert [t.validating_carrier for t in tickets] == ["IB", "IB"]


def test_an_empty_ticket_number_is_not_the_same_as_no_ticket() -> None:
    booking = _booking_with_segments(1)
    with pytest.raises(ValueError):
        booking.issue_emd("A", "")
    assert booking.emds == []


@pytest.mark.parametrize("number", ["١٢٣-١٢٣٤٥٦٧٨٩٠", "123-١٢٣٤٥٦٧٨٩٠"])
def test_ticket_digits_are_ascii(number: str) -> None:
    with pytest.raises(ValueError):
        TicketNumber.parse(number)


def test_a_ticket_for_a_stranger_is_rejected() -> None:
    booking = _booking_with_segments(1)
    with pytest.raises(ValueError):
        booking.issue_ticket("Somebody else", "125-1234567890")


def test_conjunction_tickets_belong_to_the_passenger_and_skip_unconfirmed_segments() -> None:
    segments = tuple(
        Segment("AA", "AA", status)
        for status in [Status.CONFIRMED] * 5 + [Status.WAITLISTED, Status.UNABLE_TO_CONFIRM]
    )
    booking = Booking("ABC123", ("Ana", "Bo"), segments)
    tickets = booking.issue_conjunction_tickets("Ana", "125-1234567890")
    assert [(t.passenger, t.coupons) for t in tickets] == [("Ana", 4), ("Ana", 1)]
