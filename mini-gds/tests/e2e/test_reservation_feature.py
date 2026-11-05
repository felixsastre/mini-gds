"""Runs features/reservation.feature against the running system (`scripts/dev.sh`).

The feature's minutes are compressed: see `SECONDS_PER_MINUTE` in `system.py`. Most steps are in
`conftest.py`.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest
from pytest_bdd import scenarios, then, when

from tests.e2e.conftest import reserve
from tests.e2e.system import set_seats

scenarios("reservation.feature")


@pytest.fixture(autouse=True)
def four_seats(clean_system: None) -> None:
    """The feature starts from a host with flight AA100, class M, 4 seats."""
    set_seats("AA100", "M", 4)


@when("two customers reserve class M on flight AA100 at the same time")
def _reserve_together(world: dict) -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        world["responses"] = list(pool.map(lambda _: reserve(["AA100"], "M"), range(2)))


@when("the booking worker restarts")
def _restart_worker() -> None:
    subprocess.run(["pkill", "-f", "mini_gds.worker"], check=True)  # scripts/dev.sh starts it again


@then("exactly one booking is created")
def _one_booking(world: dict) -> None:
    created = [r for r in world["responses"] if r.status_code == 201]
    assert len(created) == 1
    assert {r.status_code for r in world["responses"]} == {201, 409}
