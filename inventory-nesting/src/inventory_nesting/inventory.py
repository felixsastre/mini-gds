"""Nested booking-class inventory for a flight cabin."""

from collections.abc import Mapping
from enum import Enum
from itertools import accumulate, islice


class Nesting(Enum):
    THRESHOLD = "threshold"
    NET = "net"


class SaleRejectedError(Exception):
    """The requested seats exceed what the class can still sell."""


class Inventory:
    """Authorizations and bookings per booking class.

    Authorizations are sales limits, not a partition of the seats: they may add
    up to more than the physical capacity (overbooking). Their order is the
    nesting hierarchy, highest class first.
    """

    def __init__(self, authorizations: Mapping[str, int]) -> None:
        for name, seats in authorizations.items():
            _require_non_negative(f"authorization of {name}", seats)
        self._authorizations = dict(authorizations)
        self._bookings = dict.fromkeys(self._authorizations, 0)

    @property
    def total_sold(self) -> int:
        return sum(self._bookings.values())

    def load_bookings(self, bookings: Mapping[str, int]) -> None:
        for booking_class, seats in bookings.items():
            self._check_known(booking_class)
            _require_non_negative(f"bookings of {booking_class}", seats)
        self._bookings.update(bookings)

    def availability(self, booking_class: str, nesting: Nesting) -> int:
        self._check_known(booking_class)
        if nesting is Nesting.THRESHOLD:
            return self._authorizations[booking_class] - self.total_sold
        return self._net_availability(booking_class)

    def is_available(self, booking_class: str, nesting: Nesting) -> bool:
        """True when at least one seat can be sold in the class."""
        return self.availability(booking_class, nesting) > 0

    def sell(self, booking_class: str, seats: int, nesting: Nesting) -> None:
        _require_non_negative("seats sold", seats)
        if seats > self.availability(booking_class, nesting):
            raise SaleRejectedError(f"class {booking_class} cannot sell {seats} seats")
        self._bookings[booking_class] += seats

    def _net_availability(self, booking_class: str) -> int:
        """Authorization minus the sold in the class and lower ones, never above the class above."""
        classes = list(self._authorizations)
        sold_from = list(accumulate(self._bookings[name] for name in reversed(classes)))[::-1]
        margins = (
            self._authorizations[name] - sold for name, sold in zip(classes, sold_from, strict=True)
        )
        return min(islice(margins, classes.index(booking_class) + 1))

    def _check_known(self, booking_class: str) -> None:
        if booking_class not in self._authorizations:
            raise ValueError(f"unknown booking class: {booking_class}")


def availability_shown(computed: int, cap: int) -> int:
    """Availability sent to a distributor: capped, and never negative."""
    _require_non_negative("cap", cap)
    return max(0, min(computed, cap))


def _require_non_negative(what: str, seats: int) -> None:
    if seats < 0:
        raise ValueError(f"{what} cannot be negative: {seats}")
