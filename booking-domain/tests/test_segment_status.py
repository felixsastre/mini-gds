from pytest_bdd import given, parsers, scenarios, then, when

from booking_domain import Segment, Status

scenarios("segment_status.feature")


@given(parsers.parse("a segment with status {code}"), target_fixture="segment")
def _segment(code: str) -> Segment:
    return Segment("AA", "AA", Status(code))


@when("a segment is sold and the airline confirms it", target_fixture="segment")
def _sold_confirmed() -> Segment:
    return Segment.sell("AA", "AA", confirmed=True)


@when("a segment is sold and the airline cannot confirm it", target_fixture="segment")
def _sold_unconfirmed() -> Segment:
    return Segment.sell("AA", "AA", confirmed=False)


@when("a seat opens")
def _seat_opens(segment: Segment) -> None:
    segment.seat_opens()


@when("the segment is cancelled", target_fixture="result")
def _cancel(segment: Segment) -> str:
    try:
        segment.cancel()
    except ValueError:
        return "rejected"
    return f"status {segment.status}"


@then(parsers.parse("the segment status is {code}"))
def _status(segment: Segment, code: str) -> None:
    assert segment.status == Status(code)


@then(parsers.parse("the result is {expected}"))
def _result(result: str, expected: str) -> None:
    assert result == expected
