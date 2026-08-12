"""Production entrypoint that layers Scheduler V3 onto the frozen runtime."""
from __future__ import annotations

import asyncio
import logging

import server as runtime
from scheduler_v3 import NOT_HANDLED, SchedulerV3

LOG = logging.getLogger("sarembok.cloud.v3")
SCHEDULER = SchedulerV3(runtime.store)


def dispatch(method, params):
    result = SCHEDULER.dispatch(method, params)
    if result is not NOT_HANDLED:
        return result
    return runtime.dispatch(method, params)


async def reaper() -> None:
    while not runtime.STOP.is_set():
        try:
            await asyncio.wait_for(runtime.STOP.wait(), timeout=5)
            break
        except asyncio.TimeoutError:
            pass
        try:
            async with runtime.DB_LOCK:
                result = SCHEDULER.reap()
            if result["staleWorkers"] or result["expiredTasks"] or result["reassignedTasks"]:
                LOG.info("scheduler_reaper %s", result)
        except Exception:
            LOG.exception("scheduler_reaper_failed")


async def main() -> None:
    original_dispatch = runtime.dispatch
    runtime.dispatch = dispatch
    task = asyncio.create_task(reaper(), name="sarembok-scheduler-v3-reaper")
    try:
        await runtime.main()
    finally:
        runtime.dispatch = original_dispatch
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
