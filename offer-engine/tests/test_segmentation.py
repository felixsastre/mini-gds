import pytest
from pytest_bdd import given, parsers, scenarios, then

from offer_engine import Segment, segment_trip

scenarios("trip_purpose.feature")


@given(
    parsers.parse(
        "a round trip booked {days_ahead:d} days ahead with a stay of {stay_days:d} days"
        " for {travelers:d} travelers"
    ),
    target_fixture="trip",
)
def _round_trip(days_ahead: int, stay_days: int, travelers: int) -> tuple:
    return days_ahead, stay_days, travelers


@given(
    parsers.parse("a one-way trip booked {days_ahead:d} days ahead for {travelers:d} travelers"),
    target_fixture="trip",
)
def _one_way(days_ahead: int, travelers: int) -> tuple:
    return days_ahead, None, travelers


@then(parsers.parse("the segment is {segment}"))
def _segment(trip: tuple, segment: str) -> None:
    assert segment_trip(*trip) == Segment(segment)


@then("the trip is invalid")
def _invalid(trip: tuple) -> None:
    with pytest.raises(ValueError):
        segment_trip(*trip)
