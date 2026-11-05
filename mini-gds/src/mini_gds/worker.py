"""Runs the reservation workflows and their activities."""

import asyncio
import os
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from mini_gds.activities import Activities
from mini_gds.host_client import HttpHost
from mini_gds.workflows import TASK_QUEUE, Reservation


async def main() -> None:
    client = await Client.connect(os.environ["TEMPORAL_ADDRESS"])
    activities = Activities(HttpHost(os.environ["HOST_URL"]))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Reservation],
        activities=[
            activities.sell_seat,
            activities.release_seat,
            activities.charge_payment,
            activities.issue_ticket,
        ],
        # After a restart, work waits on the old worker's sticky queue for this long.
        sticky_queue_schedule_to_start_timeout=timedelta(seconds=2),
    ):
        print(f"worker polling task queue {TASK_QUEUE!r}", flush=True)
        await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
