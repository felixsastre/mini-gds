from dataclasses import dataclass, field, replace

from booking_domain.emd import Emd
from booking_domain.segment import Segment, Status
from booking_domain.ticket import MAX_COUPONS_PER_TICKET, Ticket, TicketNumber, issue_tickets


@dataclass
class Booking:
    gds_locator: str
    passengers: tuple[str, ...]
    segments: tuple[Segment, ...]
    airline_locator: str | None = None
    tickets: list[Ticket] = field(default_factory=list)
    emds: list[Emd] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.gds_locator:
            raise ValueError("a booking needs a GDS locator")
        if not self.passengers:
            raise ValueError("a booking needs at least one passenger")
        if not self.segments:
            raise ValueError("a booking needs at least one segment")

    def receive_airline_locator(self, locator: str) -> None:
        self.airline_locator = locator

    def issue_ticket(
        self, passenger: str, number: str, validating_carrier: str | None = None
    ) -> Ticket:
        """Issue one ticket to a passenger, with a coupon per confirmed segment.

        Raise ValueError for an unknown or already ticketed passenger, a bad or used number,
        no confirmed segment, or more than 4 confirmed segments.
        """
        coupons = self._coupons_to_ticket(passenger)
        if coupons > MAX_COUPONS_PER_TICKET:
            raise ValueError("more than 4 segments need conjunction tickets")
        ticket = Ticket(TicketNumber.parse(number), coupons, validating_carrier, passenger)
        self._add_tickets([ticket])
        return ticket

    def issue_conjunction_tickets(
        self, passenger: str, first_number: str, validating_carrier: str | None = None
    ) -> list[Ticket]:
        """Issue consecutive tickets to a passenger that cover every confirmed segment.

        Raise ValueError for an unknown or already ticketed passenger, a bad or used number,
        no confirmed segment, or more than 12 confirmed segments.
        """
        coupons = self._coupons_to_ticket(passenger)
        tickets = [
            replace(ticket, passenger=passenger)
            for ticket in issue_tickets(
                TicketNumber.parse(first_number), coupons, validating_carrier
            )
        ]
        self._add_tickets(tickets)
        return tickets

    def issue_emd(self, kind: str, ticket_number: str | None = None) -> Emd:
        """EMD-A needs a ticket of this booking; EMD-B is standalone. Raise ValueError otherwise."""
        ticket = TicketNumber.parse(ticket_number) if ticket_number is not None else None
        emd = Emd(kind, ticket)  # checks the type and whether it has the ticket it needs
        if ticket is not None and ticket not in {t.number for t in self.tickets}:
            raise ValueError(f"ticket {ticket} is not a ticket of this booking")
        self.emds.append(emd)
        return emd

    def _coupons_to_ticket(self, passenger: str) -> int:
        """The flight coupons a passenger's ticket needs: one per confirmed segment."""
        if passenger not in self.passengers:
            raise ValueError(f"{passenger!r} is not a passenger of this booking")
        if any(ticket.passenger == passenger for ticket in self.tickets):
            raise ValueError(f"{passenger!r} already has a ticket")
        coupons = sum(1 for segment in self.segments if segment.status is Status.CONFIRMED)
        if coupons == 0:
            raise ValueError("a booking with no confirmed segment cannot be ticketed")
        return coupons

    def _add_tickets(self, tickets: list[Ticket]) -> None:
        issued = {t.number for t in self.tickets}
        for ticket in tickets:
            if ticket.number in issued:
                raise ValueError(f"ticket {ticket.number} is already issued")
        self.tickets.extend(tickets)
