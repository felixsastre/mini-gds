"""The reservation workflow, run on Temporal's time-skipping test server."""

import asyncio
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from temporalio import activity
from temporalio.client import (
    WorkflowExecutionStatus,
    WorkflowHandle,
    WorkflowUpdateFailedError,
)
from temporalio.exceptions import ApplicationError
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from mini_gds.activities import Activities
from mini_gds.workflows import Reservation, ReserveRequest
from tests.unit.fakes import HOLD_SECONDS, QUEUE, FakeHost, GatedHost, LostAnswerHost


@pytest.fixture
async def env() -> AsyncIterator[WorkflowEnvironment]:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        yield environment


@activity.defn(name="issue_ticket")
async def ticketing_is_down(sale_id: str) -> str:
    raise ApplicationError("ticketing is down", non_retryable=True)


@asynccontextmanager
async def worker(
    env: WorkflowEnvironment, host: FakeHost, issue_ticket=None
) -> AsyncIterator[None]:
    acts = Activities(host)
    async with Worker(
        env.client,
        task_queue=QUEUE,
        # No cached workflows, so no sticky queue: after a worker leaves, the next one picks
        # up at once. A sticky timeout is virtual time on this server and would never pass.
        max_cached_workflows=0,
        workflows=[Reservation],
        activities=[
            acts.sell_seat,
            acts.release_seat,
            acts.charge_payment,
            issue_ticket or acts.issue_ticket,
        ],
    ):
        yield


async def start(env: WorkflowEnvironment, flights: tuple[str, ...] = ("AA100",)) -> WorkflowHandle:
    request = ReserveRequest(list(flights), "M", "Ana Souza", HOLD_SECONDS)
    return await env.client.start_workflow(
        Reservation.run, request, id=f"res-{uuid.uuid4().hex}", task_queue=QUEUE
    )


async def test_reserving_holds_a_seat_and_creates_a_booking_without_a_ticket(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        view = await (await start(env)).execute_update(Reservation.sale)
    assert view.segment_statuses == ["HK"]
    assert view.gds_locator and view.ticket is None
    assert host.available["AA100"] == 3


async def test_paying_within_the_hold_issues_a_ticket(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env)
        await handle.execute_update(Reservation.sale)
        await env.sleep(timedelta(minutes=10))
        view = await handle.execute_update(Reservation.pay, False)
        assert re.fullmatch(r"\d{3}-\d{10}", view.ticket)
        assert view.tickets == [view.ticket]
        assert (await handle.result()).ticket == view.ticket
    assert host.available["AA100"] == 3


async def test_a_hold_that_is_not_paid_expires_and_frees_the_seat(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        view = await (await start(env)).result()
    assert (view.segment_statuses, view.ticket) == (["XX"], None)
    assert host.available["AA100"] == 4


async def test_a_declined_payment_cancels_and_frees_the_seat(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env)
        await handle.execute_update(Reservation.sale)
        view = await handle.execute_update(Reservation.pay, True)
    assert (view.segment_statuses, view.ticket) == (["XX"], None)
    assert host.available["AA100"] == 4


async def test_a_class_that_cannot_be_confirmed_creates_no_booking(env) -> None:
    host = FakeHost(seats=0)
    async with worker(env, host):
        view = await (await start(env)).execute_update(Reservation.sale)
    assert (view.segment_statuses, view.gds_locator) == (["UC"], None)


async def test_paying_after_the_hold_expired_is_refused(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env)
        await handle.result()
        with pytest.raises(RPCError) as refused:  # a finished workflow takes no more updates
            await handle.execute_update(Reservation.pay, False)
    assert refused.value.status == RPCStatusCode.NOT_FOUND


async def test_the_last_seat_is_sold_once(env) -> None:
    host = FakeHost(seats=1)
    async with worker(env, host):
        handles = [await start(env), await start(env)]
        views = await asyncio.gather(*(h.execute_update(Reservation.sale) for h in handles))
    assert sorted(v.segment_statuses[0] for v in views) == ["HK", "UC"]
    assert host.available["AA100"] == 0


async def test_a_hold_survives_a_worker_restart(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env)
        await handle.execute_update(Reservation.sale)
    await env.sleep(timedelta(minutes=5))  # nobody is polling: the hold keeps counting
    async with worker(env, host):
        await env.sleep(timedelta(minutes=5))
        view = await handle.execute_update(Reservation.pay, False)
    assert view.ticket is not None
    assert (await handle.describe()).status == WorkflowExecutionStatus.COMPLETED


CONNECTION = ("AA100", "AA200")


async def test_a_connection_takes_a_seat_on_each_leg(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        view = await (await start(env, CONNECTION)).execute_update(Reservation.sale)
    assert view.segment_statuses == ["HK", "HK"]
    assert (host.available["AA100"], host.available["AA200"]) == (3, 3)


async def test_a_connection_that_fails_on_a_later_leg_is_sold_on_none(env) -> None:
    host = FakeHost(seats={"AA100": 4, "AA200": 0})
    async with worker(env, host):
        view = await (await start(env, CONNECTION)).execute_update(Reservation.sale)
    assert (view.segment_statuses, view.gds_locator) == (["UC"], None)
    assert host.available["AA100"] == 4
    assert host.sales == {}


async def test_a_connection_that_is_paid_gets_one_ticket(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env, CONNECTION)
        await handle.execute_update(Reservation.sale)
        view = await handle.execute_update(Reservation.pay, False)
    assert re.fullmatch(r"\d{3}-\d{10}", view.ticket)
    assert view.segment_statuses == ["HK", "HK"]


async def test_an_unpaid_connection_gives_back_both_seats(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        view = await (await start(env, CONNECTION)).result()
    assert view.segment_statuses == ["XX", "XX"]
    assert (host.available["AA100"], host.available["AA200"]) == (4, 4)


async def test_a_host_failure_on_a_later_leg_gives_back_every_leg_it_may_have_sold(env) -> None:
    host = LostAnswerHost(seats=4, flaky={"AA200"})
    async with worker(env, host):
        view = await (await start(env, CONNECTION)).execute_update(Reservation.sale)
    assert (view.segment_statuses, view.gds_locator) == (["UC"], None)
    assert host.sales == {}
    assert (host.available["AA100"], host.available["AA200"]) == (4, 4)


async def test_paying_while_an_expired_hold_is_being_cancelled_is_refused(env) -> None:
    host = GatedHost(seats=4)
    async with worker(env, host):
        handle = await start(env)
        await handle.execute_update(Reservation.sale)
        try:
            await env.sleep(timedelta(seconds=HOLD_SECONDS + 1))
            await host.release_started.wait()  # the cancellation is under way
            with pytest.raises(WorkflowUpdateFailedError):
                await handle.execute_update(Reservation.pay, False)
        finally:
            host.let_release_go.set()
        view = await handle.result()
    assert (view.segment_statuses, view.ticket) == (["XX"], None)
    assert host.available["AA100"] == 4


async def test_a_ticketing_failure_after_payment_cancels_and_frees_the_seat(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host, issue_ticket=ticketing_is_down):
        handle = await start(env)
        await handle.execute_update(Reservation.sale)
        view = await handle.execute_update(Reservation.pay, False)
        await handle.result()
    assert (view.segment_statuses, view.ticket) == (["XX"], None)
    assert host.available["AA100"] == 4


async def test_paying_for_a_long_itinerary_issues_conjunction_tickets(env) -> None:
    flights = tuple(f"AA{number}" for number in range(100, 106))  # 6 legs: 2 tickets
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env, flights)
        await handle.execute_update(Reservation.sale)
        view = await handle.execute_update(Reservation.pay, False)
    assert re.fullmatch(r"\d{3}-\d{10}", view.ticket)
    assert view.segment_statuses == ["HK"] * 6
    assert len(view.tickets) == 2 and view.tickets[0] == view.ticket
    first, second = (int(number.split("-")[1]) for number in view.tickets)
    assert second == first + 1


async def test_a_flight_the_domain_refuses_gives_the_seat_back_instead_of_hanging(env) -> None:
    host = FakeHost(seats=4)
    async with worker(env, host):
        handle = await start(env, ("aa100",))  # the host sells it, a booking cannot hold it
        view = await asyncio.wait_for(handle.execute_update(Reservation.sale), timeout=20)
    assert (view.segment_statuses, view.gds_locator) == (["UC"], None)
    assert host.available["aa100"] == 4


@activity.defn(name="issue_ticket")
async def ticket_numbers_run_out(sale_id: str) -> str:
    return "999-9999999999"  # six legs need a second ticket, and no number follows this one


async def test_a_ticket_the_domain_refuses_cancels_the_booking(env) -> None:
    flights = tuple(f"AA{number}" for number in range(100, 106))
    host = FakeHost(seats=4)
    async with worker(env, host, issue_ticket=ticket_numbers_run_out):
        handle = await start(env, flights)
        await handle.execute_update(Reservation.sale)
        view = await asyncio.wait_for(handle.execute_update(Reservation.pay, False), timeout=20)
    assert (view.segment_statuses, view.ticket) == (["XX"] * 6, None)
    assert all(host.available[flight] == 4 for flight in flights)
