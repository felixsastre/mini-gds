"""TemporalReservations against Temporal's time-skipping test server."""

from datetime import timedelta

import pytest
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from mini_gds.activities import Activities
from mini_gds.reservations import (
    HoldClosedError,
    ReservationNotFoundError,
    ReservationsUnavailableError,
    TemporalReservations,
)
from mini_gds.workflows import Reservation
from tests.unit.fakes import QUEUE, FakeHost


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        yield environment


def reservations(env: WorkflowEnvironment) -> TemporalReservations:
    async def connect():
        return env.client

    return TemporalReservations(connect, QUEUE, hold_seconds=15 * 60)


def worker(env: WorkflowEnvironment, host: FakeHost) -> Worker:
    acts = Activities(host)
    return Worker(
        env.client,
        task_queue=QUEUE,
        max_cached_workflows=0,
        workflows=[Reservation],
        activities=[acts.sell_seat, acts.release_seat, acts.charge_payment, acts.issue_ticket],
    )


async def test_reserve_pay_and_read(env) -> None:
    service = reservations(env)
    async with worker(env, FakeHost(seats=4)):
        reservation_id, view = await service.reserve(["AA100"], "M", "Ana")
        assert view.segment_statuses == ["HK"]
        paid = await service.pay(reservation_id, decline=False)
        assert paid.ticket is not None
        assert (await service.get(reservation_id)).ticket == paid.ticket


async def test_paying_after_the_hold_closed_raises_hold_closed(env) -> None:
    service = reservations(env)
    async with worker(env, FakeHost(seats=4)):
        reservation_id, _ = await service.reserve(["AA100"], "M", "Ana")
        await env.sleep(timedelta(minutes=16))
        with pytest.raises(HoldClosedError):
            await service.pay(reservation_id, decline=False)


async def test_reading_an_unknown_reservation_raises_not_found(env) -> None:
    async with worker(env, FakeHost(seats=4)):
        with pytest.raises(ReservationNotFoundError):
            await reservations(env).get("res-does-not-exist")


class ClientWhoseWorkflowHasEnded:
    """Hands back the workflow only after it has finished, so the next update comes too late."""

    def __init__(self, client) -> None:
        self._client = client

    async def start_workflow(self, *args, **kwargs):
        handle = await self._client.start_workflow(*args, **kwargs)
        await handle.result()
        return handle


async def test_a_sale_the_airline_refused_still_answers_when_the_workflow_already_ended(
    env,
) -> None:
    async def connect():
        return ClientWhoseWorkflowHasEnded(env.client)

    service = TemporalReservations(connect, QUEUE, hold_seconds=15 * 60)
    async with worker(env, FakeHost(seats=0)):
        _, view = await service.reserve(["AA100"], "M", "Ana")
    assert (view.segment_statuses, view.gds_locator) == (["UC"], None)


def temporal_is_down() -> RPCError:
    return RPCError("temporal is down", RPCStatusCode.UNAVAILABLE, b"")


class DownHandle:
    async def query(self, *args, **kwargs):
        raise temporal_is_down()

    async def execute_update(self, *args, **kwargs):
        raise temporal_is_down()

    async def describe(self, *args, **kwargs):
        raise temporal_is_down()


class DownClient:
    async def start_workflow(self, *args, **kwargs):
        raise temporal_is_down()

    def get_workflow_handle_for(self, *args, **kwargs):
        return DownHandle()


@pytest.fixture
def down() -> TemporalReservations:
    async def connect():
        return DownClient()

    return TemporalReservations(connect, QUEUE, hold_seconds=15 * 60)


async def test_reserving_while_temporal_is_down_raises_unavailable(down) -> None:
    with pytest.raises(ReservationsUnavailableError):
        await down.reserve(["AA100"], "M", "Ana")


async def test_reading_while_temporal_is_down_is_not_a_missing_reservation(down) -> None:
    with pytest.raises(ReservationsUnavailableError):
        await down.get("res-1")


async def test_paying_while_temporal_is_down_is_not_a_missing_reservation(down) -> None:
    with pytest.raises(ReservationsUnavailableError):
        await down.pay("res-1", decline=False)


class RefusingHandle:
    """A workflow handle whose Temporal server answers every call with `status`."""

    def __init__(self, status: RPCStatusCode) -> None:
        self.status = status

    async def execute_update(self, *args, **kwargs):
        raise RPCError("refused", self.status, b"")

    async def describe(self):
        return object()  # the workflow exists


class RefusingClient:
    def __init__(self, status: RPCStatusCode) -> None:
        self.handle = RefusingHandle(status)

    def get_workflow_handle_for(self, *args, **kwargs) -> RefusingHandle:
        return self.handle


async def test_a_temporal_that_cannot_be_reached_is_unavailable_not_a_crash() -> None:
    async def connect():
        raise RuntimeError("Failed client connect")

    service = TemporalReservations(connect, QUEUE, hold_seconds=900)
    for call in (
        service.reserve(["AA100"], "M", "Ana"),
        service.pay("res-1", decline=False),
        service.get("res-1"),
    ):
        with pytest.raises(ReservationsUnavailableError):
            await call


async def test_a_temporal_failure_while_paying_is_not_reported_as_a_closed_hold() -> None:
    async def connect():
        return RefusingClient(RPCStatusCode.UNAVAILABLE)

    with pytest.raises(ReservationsUnavailableError):
        await TemporalReservations(connect, QUEUE, hold_seconds=900).pay("res-1", decline=False)
