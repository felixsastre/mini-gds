from pytest_bdd import given, parsers, scenarios, then, when

from booking_domain import Segment, Status, Ticket, TicketNumber

scenarios("carriers.feature")


@given(
    parsers.parse("a segment sold under {marketing} and operated by {operating}"),
    target_fixture="segment",
)
def _segment(marketing: str, operating: str) -> Segment:
    return Segment(marketing, operating, Status.CONFIRMED)


@given(parsers.parse("the ticket is validated by {carrier}"), target_fixture="ticket")
def _ticket(carrier: str) -> Ticket:
    return Ticket(TicketNumber("125", "1234567890"), coupons=1, validating_carrier=carrier)


@then(parsers.parse("the marketing carrier is {carrier}"))
def _marketing(segment: Segment, carrier: str) -> None:
    assert segment.marketing_carrier == carrier


@then(parsers.parse("the operating carrier is {carrier}"))
def _operating(segment: Segment, carrier: str) -> None:
    assert segment.operating_carrier == carrier


@then(parsers.parse("the validating carrier is {carrier}"))
def _validating(ticket: Ticket, carrier: str) -> None:
    assert ticket.validating_carrier == carrier


@when(
    parsers.parse("a segment is sold under {marketing} and operated by {operating}"),
    target_fixture="outcome",
)
def _sold(marketing: str, operating: str) -> str:
    try:
        Segment(marketing, operating, Status.CONFIRMED)
    except ValueError:
        return "rejected"
    return "accepted"


@when(parsers.parse("a ticket is validated by {carrier}"), target_fixture="outcome")
def _validated(carrier: str) -> str:
    try:
        Ticket(TicketNumber("125", "1234567890"), coupons=1, validating_carrier=carrier)
    except ValueError:
        return "rejected"
    return "accepted"


@then(parsers.re(r"the (?:segment|ticket) is (?P<expected>accepted|rejected)"))
def _outcome(outcome: str, expected: str) -> None:
    assert outcome == expected
