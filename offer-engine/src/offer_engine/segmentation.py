from enum import StrEnum


class Segment(StrEnum):
    BUSINESS = "business"
    FAMILY = "family"
    COUPLE = "couple"
    LEISURE = "leisure"
    ONE_WAY = "one-way"


def segment_trip(days_ahead: int, stay_days: int | None, travelers: int) -> Segment:
    """Return the single segment of a trip. `stay_days` is None for a one-way trip.

    Raise ValueError for fewer than 1 traveler or a negative number of days.
    """
    if travelers < 1:
        raise ValueError(f"a trip has at least 1 traveler, not {travelers}")
    if days_ahead < 0 or (stay_days is not None and stay_days < 0):
        raise ValueError("days ahead and days of stay cannot be negative")
    if stay_days is None:
        return Segment.ONE_WAY
    if travelers == 1 and days_ahead <= 6 and stay_days <= 1:
        return Segment.BUSINESS
    if travelers > 2:
        return Segment.FAMILY
    if travelers == 2:
        return Segment.COUPLE
    return Segment.LEISURE
