"""Where the running system is, and helpers shared by the end-to-end steps."""

import os
import time
from collections.abc import Callable

import httpx2 as httpx

HOST = os.environ.get("HOST_URL", "http://localhost:18000")
CACHE = os.environ.get("CACHE_URL", "http://localhost:18081")
API = os.environ.get("API_URL", "http://localhost:18080")

# The api's hold is 15 minutes when HOLD_SECONDS is 900. The end-to-end run compresses time:
# with HOLD_SECONDS=30, one minute of the feature lasts two seconds.
HOLD_SECONDS = int(os.environ.get("HOLD_SECONDS", "900"))
SECONDS_PER_MINUTE = HOLD_SECONDS / 15


def ok(response: httpx.Response) -> httpx.Response:
    response.raise_for_status()
    return response


def reset_system() -> None:
    ok(httpx.post(f"{HOST}/admin/reset"))
    ok(httpx.post(f"{CACHE}/admin/reset"))


def set_seats(flight: str, booking_class: str, seats: int) -> None:
    ok(
        httpx.put(
            f"{HOST}/admin/flights/{flight}/classes/{booking_class}/seats", json={"seats": seats}
        )
    )


def eventually(check: Callable[[], None], seconds: float = 4.0) -> None:
    """Run an assertion until it holds: the system settles a moment after a step."""
    deadline = time.monotonic() + seconds
    while True:
        try:
            return check()
        except AssertionError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.25)
