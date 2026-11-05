"""How the worker talks to the airline host service."""

from typing import Protocol

import httpx2 as httpx


class HostClient(Protocol):
    async def sell(self, flight: str, booking_class: str, sale_id: str) -> bool:
        """Sell one seat. True when sold (also when `sale_id` was already sold), False when
        the airline cannot confirm it."""
        ...

    async def release(self, flight: str, sale_id: str) -> None:
        """Give the seat of `sale_id` back. Releasing twice changes nothing."""
        ...


class HttpHost:
    def __init__(self, base_url: str) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=5.0)

    async def sell(self, flight: str, booking_class: str, sale_id: str) -> bool:
        response = await self._http.post(
            f"/flights/{flight}/classes/{booking_class}/sales", json={"sale_id": sale_id}
        )
        if response.status_code == 409:
            return False
        response.raise_for_status()
        return True

    async def release(self, flight: str, sale_id: str) -> None:
        response = await self._http.delete(f"/flights/{flight}/sales/{sale_id}")
        response.raise_for_status()
