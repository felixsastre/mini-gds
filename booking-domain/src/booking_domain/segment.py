import re
from dataclasses import dataclass
from enum import StrEnum

CARRIER_CODE = re.compile(r"[A-Z0-9]{2}")


def require_carrier_code(carrier: str) -> None:
    """Raise ValueError unless the carrier is 2 capital letters or digits."""
    if not CARRIER_CODE.fullmatch(carrier):
        raise ValueError(f"carrier must be 2 capital letters or digits: {carrier!r}")


class Status(StrEnum):
    CONFIRMED = "HK"
    WAITLISTED = "HL"
    UNABLE_TO_CONFIRM = "UC"
    CANCELLED = "XX"


@dataclass
class Segment:
    marketing_carrier: str
    operating_carrier: str
    status: Status

    def __post_init__(self) -> None:
        require_carrier_code(self.marketing_carrier)
        require_carrier_code(self.operating_carrier)

    @classmethod
    def sell(cls, marketing_carrier: str, operating_carrier: str, confirmed: bool) -> "Segment":
        status = Status.CONFIRMED if confirmed else Status.UNABLE_TO_CONFIRM
        return cls(marketing_carrier, operating_carrier, status)

    def seat_opens(self) -> None:
        """A waitlisted segment becomes confirmed; any other status is unchanged."""
        if self.status is Status.WAITLISTED:
            self.status = Status.CONFIRMED

    def cancel(self) -> None:
        """Cancel a confirmed or waitlisted segment; UC and XX are final."""
        if self.status in (Status.CANCELLED, Status.UNABLE_TO_CONFIRM):
            raise ValueError(f"a segment with status {self.status} cannot be cancelled")
        self.status = Status.CANCELLED
