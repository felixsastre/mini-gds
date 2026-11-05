"""The steps of a reservation that touch the outside world. Temporal may retry them."""

import hashlib

from temporalio import activity
from temporalio.exceptions import ApplicationError

from mini_gds.host_client import HostClient

AIRLINE_CODE = "999"  # a synthetic airline code, not a real one


class Activities:
    def __init__(self, host: HostClient) -> None:
        self._host = host

    @activity.defn
    async def sell_seat(self, flight: str, booking_class: str, sale_id: str) -> bool:
        return await self._host.sell(flight, booking_class, sale_id)

    @activity.defn
    async def release_seat(self, flight: str, sale_id: str) -> None:
        await self._host.release(flight, sale_id)

    @activity.defn
    async def charge_payment(self, decline: bool) -> None:
        """Simulated payment: it either succeeds or is declined."""
        if decline:
            raise ApplicationError("payment declined", non_retryable=True)

    @activity.defn
    async def issue_ticket(self, sale_id: str) -> str:
        """Simulated ticketing: a 3 + 10 digit number derived from the sale, so a retry
        issues the same number."""
        document = int(hashlib.sha256(sale_id.encode()).hexdigest(), 16) % 10**10
        return f"{AIRLINE_CODE}-{document:010d}"
