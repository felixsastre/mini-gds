"""How the api talks to the availability cache service."""

from typing import Protocol

import httpx2 as httpx

Key = tuple[str, str]  # (flight, booking class)


class CacheUnavailableError(Exception):
    """The availability cache service did not answer, or failed."""


class HostUnavailableError(Exception):
    """The airline host could not answer about a class: that is not the same as closed."""


class AvailabilityCache(Protocol):
    def seats(self, flight: str, booking_class: str) -> int:
        """Seats left; raise HostUnavailableError when the airline cannot answer."""
        ...

    def wash(self, offers: list[Key], top: int) -> tuple[list[Key], int]:
        """Check the first `top` offers against the airline; return those to show and the
        number of open-wrong errors caught."""
        ...


class HttpCache:
    def __init__(self, base_url: str) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=5.0)

    def seats(self, flight: str, booking_class: str) -> int:
        response = self._send(
            "GET", "/availability", params={"flight": flight, "class": booking_class}
        )
        if response.status_code == httpx.codes.SERVICE_UNAVAILABLE:
            raise HostUnavailableError
        return self._checked(response).json()["seats"]

    def wash(self, offers: list[Key], top: int) -> tuple[list[Key], int]:
        payload = {"offers": [{"flight": f, "class": c} for f, c in offers], "top": top}
        body = self._checked(self._send("POST", "/wash", json=payload)).json()
        return [(o["flight"], o["class"]) for o in body["shown"]], body["open_wrong_caught"]

    def _send(self, method: str, path: str, **options) -> httpx.Response:
        try:
            return self._http.request(method, path, **options)
        except httpx.TransportError as error:  # not reachable, refused, or too slow
            raise CacheUnavailableError from error

    @staticmethod
    def _checked(response: httpx.Response) -> httpx.Response:
        if response.is_server_error:
            raise CacheUnavailableError(f"the cache answered {response.status_code}")
        response.raise_for_status()
        return response
