"""A reservation: sell a seat, hold it until it is paid or the hold expires."""

import hashlib
from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from booking_domain import Booking, Segment, Status

    from mini_gds.activities import Activities

TASK_QUEUE = "reservations"
ACTIVITY_TIMEOUT = timedelta(seconds=10)
SELL_RETRIES = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(milliseconds=500))


@dataclass
class ReserveRequest:
    flights: list[str]  # one per leg, in travel order
    booking_class: str
    passenger: str
    hold_seconds: int


@dataclass
class BookingView:
    segment_statuses: list[str]  # per leg: HK held, XX cancelled; ["UC"] if not confirmed
    gds_locator: str | None  # None when no booking was created
    ticket: str | None  # the main ticket: the first one
    tickets: list[str] = field(default_factory=list)  # every ticket, in order


@workflow.defn
class Reservation:
    def __init__(self) -> None:
        self._request: ReserveRequest | None = None
        self._booking: Booking | None = None
        self._view: BookingView | None = None
        self._sold: list[tuple[str, str]] = []  # (flight, sale id) of every leg sold so far
        self._state = "selling"  # selling, held, paying, cancelling, closed

    @workflow.run
    async def run(self, request: ReserveRequest) -> BookingView:
        self._request = request
        if not await self._sell_every_leg():
            return await self._give_up()

        try:
            self._booking = Booking(
                gds_locator=hashlib.sha256(self._sale_id().encode()).hexdigest()[:6].upper(),
                passengers=(request.passenger,),
                segments=tuple(
                    Segment.sell(flight[:2], flight[:2], confirmed=True)
                    for flight in request.flights
                ),
            )
        except ValueError:  # the airline sold it, but no booking can hold it: give it back
            return await self._give_up()
        self._state = "held"
        self._refresh()

        try:
            await workflow.wait_condition(
                lambda: self._state != "held", timeout=timedelta(seconds=request.hold_seconds)
            )
        except TimeoutError:
            if self._state == "held":  # a payment that already started finishes the booking
                await self._cancel()
        await workflow.wait_condition(lambda: self._state == "closed")
        return await self._finish()

    async def _give_up(self) -> BookingView:
        """No booking exists: give back every leg sold and answer that it is unconfirmed."""
        await self._release_sold()
        self._view = BookingView([Status.UNABLE_TO_CONFIRM.value], None, None)
        self._state = "closed"
        return await self._finish()

    @workflow.update
    async def sale(self) -> BookingView:
        """The outcome of the sale, once the airline has answered."""
        await workflow.wait_condition(lambda: self._view is not None)
        return self._view

    @workflow.update
    async def pay(self, decline: bool) -> BookingView:
        # The validator runs before the handler body, so two payments delivered together both
        # pass it: only the first may start.
        self._check_hold_is_open()
        self._state = "paying"
        try:
            await workflow.execute_activity_method(
                Activities.charge_payment,
                decline,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            number = await workflow.execute_activity_method(
                Activities.issue_ticket,
                self._sale_id(),
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            self._booking.issue_conjunction_tickets(
                self._request.passenger, number, validating_carrier=self._request.flights[0][:2]
            )
        except (ActivityError, ValueError):
            # A declined payment or a ticket that cannot be issued, by the airline or by the
            # booking, gives the seats back. Payment is simulated, so there is nothing to refund.
            await self._cancel()
            return self._view
        self._state = "closed"
        self._refresh()
        return self._view

    @pay.validator
    def _validate_pay(self, decline: bool) -> None:
        self._check_hold_is_open()

    def _check_hold_is_open(self) -> None:
        if self._state != "held":
            raise ApplicationError("the hold is not open", type="HoldClosed")

    @workflow.query
    def booking(self) -> BookingView | None:
        return self._view

    async def _sell_every_leg(self) -> bool:
        """Sell the legs in order; stop at the first one the airline cannot confirm.

        A leg whose answer never arrives may still have been sold, so it is recorded before
        the attempt and given back with the others."""
        for index, flight in enumerate(self._request.flights):
            sale_id = self._leg_sale_id(index)
            self._sold.append((flight, sale_id))
            try:
                sold = await workflow.execute_activity_method(
                    Activities.sell_seat,
                    args=[flight, self._request.booking_class, sale_id],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    retry_policy=SELL_RETRIES,
                )
            except ActivityError:
                return False
            if not sold:
                self._sold.pop()
                return False
        return True

    async def _release_sold(self) -> None:
        """Give back every leg sold so far, last first."""
        while self._sold:
            flight, sale_id = self._sold[-1]
            await workflow.execute_activity_method(
                Activities.release_seat,
                args=[flight, sale_id],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            self._sold.pop()

    async def _cancel(self) -> None:
        """Compensate: cancel the segments and give the seats back to the airline."""
        self._state = "cancelling"  # a payment must not start while the seats are given back
        for segment in self._booking.segments:
            segment.cancel()
        await self._release_sold()
        self._state = "closed"
        self._refresh()

    async def _finish(self) -> BookingView:
        """End only once every update has answered, so no client is left with an error."""
        await workflow.wait_condition(workflow.all_handlers_finished)
        return self._view

    def _sale_id(self) -> str:
        return workflow.info().workflow_id

    def _leg_sale_id(self, index: int) -> str:
        return f"{self._sale_id()}:{index}"

    def _refresh(self) -> None:
        booking = self._booking
        tickets = [str(ticket.number) for ticket in booking.tickets]
        statuses = [segment.status.value for segment in booking.segments]
        self._view = BookingView(
            statuses, booking.gds_locator, tickets[0] if tickets else None, tickets
        )
