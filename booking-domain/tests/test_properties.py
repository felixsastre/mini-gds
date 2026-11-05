from hypothesis import given
from hypothesis import strategies as st

from booking_domain import Segment, Status, TicketNumber, issue_tickets
from booking_domain.ticket import MAX_DOCUMENT

ticket_numbers = st.builds(
    TicketNumber,
    airline_code=st.integers(0, 999).map(lambda n: f"{n:03d}"),
    document=st.integers(0, MAX_DOCUMENT).map(lambda n: f"{n:010d}"),
)


@given(number=ticket_numbers)
def test_a_ticket_number_survives_a_round_trip_through_text(number: TicketNumber):
    assert TicketNumber.parse(str(number)) == number


# Up to 3 conjunction tickets need two more document numbers after the first.
room_for_conjunction = ticket_numbers.filter(lambda n: int(n.document) <= MAX_DOCUMENT - 2)


@given(first=room_for_conjunction, coupons=st.integers(1, 12))
def test_conjunction_tickets_cover_every_coupon_with_consecutive_numbers(
    first: TicketNumber, coupons: int
):
    tickets = issue_tickets(first, coupons)
    assert sum(t.coupons for t in tickets) == coupons
    assert all(1 <= t.coupons <= 4 for t in tickets)
    expected = first
    for ticket in tickets:
        assert ticket.number == expected
        expected = expected.next()


@given(status=st.sampled_from(Status))
def test_an_opening_seat_only_changes_a_waitlisted_segment(status: Status):
    segment = Segment("AA", "AA", status)
    segment.seat_opens()
    expected = Status.CONFIRMED if status is Status.WAITLISTED else status
    assert segment.status is expected


def test_the_last_document_number_can_still_be_a_single_ticket():
    last = TicketNumber("125", "9999999999")
    assert [t.number for t in issue_tickets(last, 4)] == [last]
