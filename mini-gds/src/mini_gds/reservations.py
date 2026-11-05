"""Reservations as Temporal workflows: the port the api uses and its Temporal adapter."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Protocol

from temporalio.client import (
    Client,
    WorkflowFailureError,
    WorkflowHandle,
    WorkflowUpdateFailedError,
)
from temporalio.service import RPCError, RPCStatusCode

from mini_gds.workflows import BookingView, Reservation, ReserveRequest


class HoldClosedError(Exception):
    """The hold is not open: it expired or the reservation was already settled."""


class ReservationNotFoundError(Exception):
    """No reservation has this id."""


class ReservationsUnavailableError(Exception):
    """Temporal did not answer, or the reservation workflow failed."""


class Reservations(Protocol):
    async def reserve(
        self, flights: list[str], booking_class: str, passenger: str
    ) -> tuple[str, BookingView]:
        """Sell a seat on each flight and hold them. Returns the reservation id and the
        outcome."""
        ...

    async def pay(self, reservation_id: str, decline: bool) -> BookingView: ...

    async def get(self, reservation_id: str) -> BookingView: ...


class TemporalReservations:
    def __init__(
        self, connect: Callable[[], Awaitable[Client]], task_queue: str, hold_seconds: int
    ) -> None:
        self._connect = connect
        self._task_queue = task_queue
        self._hold_seconds = hold_seconds
        self._client: Client | None = None

    async def reserve(
        self, flights: list[str], booking_class: str, passenger: str
    ) -> tuple[str, BookingView]:
        reservation_id = f"res-{uuid.uuid4().hex[:12]}"
        request = ReserveRequest(flights, booking_class, passenger, self._hold_seconds)
        try:
            handle = await (await self._temporal()).start_workflow(
                Reservation.run, request, id=reservation_id, task_queue=self._task_queue
            )
            return reservation_id, await self._sale(handle)
        except (RPCError, WorkflowFailureError) as error:
            raise ReservationsUnavailableError from error

    async def pay(self, reservation_id: str, decline: bool) -> BookingView:
        handle = await self._handle(reservation_id)
        try:
            return await handle.execute_update(Reservation.pay, decline)
        except WorkflowUpdateFailedError as error:
            raise HoldClosedError from error
        except RPCError as error:
            # Only "not found" means the workflow finished or never existed; any other answer
            # says nothing about the hold.
            if error.status != RPCStatusCode.NOT_FOUND:
                raise ReservationsUnavailableError from error
            if await self._exists(handle):
                raise HoldClosedError from error
            raise ReservationNotFoundError from error

    async def get(self, reservation_id: str) -> BookingView:
        handle = await self._handle(reservation_id)
        try:
            view = await handle.query(Reservation.booking)
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                raise ReservationNotFoundError from error
            raise ReservationsUnavailableError from error
        if view is None:  # the airline has not answered yet
            raise ReservationNotFoundError
        return view

    async def _temporal(self) -> Client:
        if self._client is None:
            try:
                self._client = await self._connect()
            except (RuntimeError, OSError) as error:  # what Temporal's client raises when down
                raise ReservationsUnavailableError from error
        return self._client

    async def _handle(self, reservation_id: str) -> WorkflowHandle:
        client = await self._temporal()
        return client.get_workflow_handle_for(Reservation.run, reservation_id)

    @staticmethod
    async def _sale(handle: WorkflowHandle) -> BookingView:
        try:
            return await handle.execute_update(Reservation.sale)
        except (RPCError, WorkflowUpdateFailedError):
            # The workflow ended before it could answer the update: its result is the answer.
            return await handle.result()

    @staticmethod
    async def _exists(handle: WorkflowHandle) -> bool:
        try:
            await handle.describe()
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return False
            raise ReservationsUnavailableError from error
        return True
