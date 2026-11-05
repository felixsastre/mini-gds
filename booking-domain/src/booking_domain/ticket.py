import re
from dataclasses import dataclass

from booking_domain.segment import require_carrier_code

MAX_COUPONS_PER_TICKET = 4
MAX_COUPONS = 12
MAX_DOCUMENT = 9_999_999_999

_AIRLINE_CODE = re.compile(r"[0-9]{3}")
_DOCUMENT = re.compile(r"[0-9]{10}")


@dataclass(frozen=True)
class TicketNumber:
    airline_code: str  # 3 digits
    document: str  # 10 digits

    def __post_init__(self) -> None:
        if not _AIRLINE_CODE.fullmatch(self.airline_code) or not _DOCUMENT.fullmatch(self.document):
            raise ValueError("a ticket number is 3 digits of airline code and 10 of document")

    @classmethod
    def parse(cls, text: str) -> "TicketNumber":
        """Parse "125-1234567890"; raise ValueError if it is not 3 + 10 digits."""
        airline_code, _, document = text.partition("-")
        return cls(airline_code, document)

    def __str__(self) -> str:
        return f"{self.airline_code}-{self.document}"

    def next(self) -> "TicketNumber":
        """The consecutive number, for a conjunction ticket; ValueError after the last one."""
        following = int(self.document) + 1
        if following > MAX_DOCUMENT:
            raise ValueError(f"no ticket number follows {self}")
        return TicketNumber(self.airline_code, str(following).zfill(10))


@dataclass(frozen=True)
class Ticket:
    number: TicketNumber
    coupons: int
    validating_carrier: str | None = None
    passenger: str | None = None  # set by Booking, which issues a ticket per passenger

    def __post_init__(self) -> None:
        if not 1 <= self.coupons <= MAX_COUPONS_PER_TICKET:
            raise ValueError(
                f"a ticket holds 1 to {MAX_COUPONS_PER_TICKET} coupons, not {self.coupons}"
            )
        if self.validating_carrier is not None:
            require_carrier_code(self.validating_carrier)


def issue_tickets(
    first: TicketNumber, coupons: int, validating_carrier: str | None = None
) -> list[Ticket]:
    """Split flight coupons into consecutive tickets of at most 4 coupons each."""
    if not 1 <= coupons <= MAX_COUPONS:
        raise ValueError(f"an itinerary has 1 to {MAX_COUPONS} flight coupons, not {coupons}")
    tickets = []
    number = first
    for left in range(coupons, 0, -MAX_COUPONS_PER_TICKET):
        if tickets:
            number = number.next()
        tickets.append(Ticket(number, min(left, MAX_COUPONS_PER_TICKET), validating_carrier))
    return tickets
