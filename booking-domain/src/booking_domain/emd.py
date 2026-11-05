from dataclasses import dataclass

from booking_domain.ticket import TicketNumber


@dataclass(frozen=True)
class Emd:
    kind: str  # "A" associated with a ticket, "B" standalone
    ticket: TicketNumber | None

    def __post_init__(self) -> None:
        if self.kind not in ("A", "B"):
            raise ValueError(f"EMD type must be A or B, not {self.kind!r}")
        if self.kind == "A" and self.ticket is None:
            raise ValueError("an EMD-A is associated with a ticket")
        if self.kind == "B" and self.ticket is not None:
            raise ValueError("an EMD-B is standalone, so it has no ticket")
