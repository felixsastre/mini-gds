"""Test doubles shared by the workflow tests."""

import asyncio
from collections import defaultdict

QUEUE = "reservations-test"
HOLD_SECONDS = 15 * 60


class FakeHost:
    """An airline with seats per flight and idempotent sales, like the real host.

    `seats` is the same number for every flight, or a number per flight.
    """

    def __init__(self, seats: int | dict[str, int]) -> None:
        per_flight = seats if isinstance(seats, dict) else {}
        default = seats if isinstance(seats, int) else 0
        self.available: dict[str, int] = defaultdict(lambda: default, per_flight)
        self.sales: dict[str, str] = {}  # sale id -> flight

    async def sell(self, flight: str, booking_class: str, sale_id: str) -> bool:
        if sale_id in self.sales:
            return True
        if self.available[flight] == 0:
            return False
        self.available[flight] -= 1
        self.sales[sale_id] = flight
        return True

    async def release(self, flight: str, sale_id: str) -> None:
        if self.sales.pop(sale_id, None) is not None:
            self.available[flight] += 1


class LostAnswerHost(FakeHost):
    """An airline that sells on the `flaky` flights but whose answer never arrives."""

    def __init__(self, seats: int | dict[str, int], flaky: set[str]) -> None:
        super().__init__(seats)
        self.flaky = flaky

    async def sell(self, flight: str, booking_class: str, sale_id: str) -> bool:
        sold = await super().sell(flight, booking_class, sale_id)
        if flight in self.flaky:
            raise ConnectionError("the answer was lost")
        return sold


class GatedHost(FakeHost):
    """An airline whose releases wait until the test lets them go."""

    def __init__(self, seats: int | dict[str, int]) -> None:
        super().__init__(seats)
        self.release_started = asyncio.Event()
        self.let_release_go = asyncio.Event()

    async def release(self, flight: str, sale_id: str) -> None:
        self.release_started.set()
        await self.let_release_go.wait()
        await super().release(flight, sale_id)
