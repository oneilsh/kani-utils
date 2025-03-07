import asyncio
from typing import Generator
from kani.streaming import StreamManager
import nest_asyncio

def _seconds_to_days_hours(ttl_seconds):
    # we need to convert the time to a human-readable format, e.g. 28 days, 18 hours (rounded to nearest hour)
    # we don't want the default datetime.timedelta format
    ttl_days = int(ttl_seconds // (60 * 60 * 24))
    ttl_hours = int((ttl_seconds % (60 * 60 * 24)) // (60 * 60))
    # only show days and hours if greater than 0, add 's' if greater than 1
    ttl_human = ""
    if ttl_days > 0:
        ttl_human = f"{ttl_days} day{'s' if ttl_days > 1 else ''}"
    if ttl_hours > 0:
        if ttl_days > 0:
            ttl_human += f", {ttl_hours} hour{'s' if ttl_hours > 1 else ''}"
        else:
            ttl_human = f"{ttl_hours} hour{'s' if ttl_hours > 1 else ''}"
     
    return ttl_human


def _sync_generator_from_kani_streammanager(kani_stream: StreamManager) -> Generator:
    """
    Converts an asynchronous StreamManager from Kani to a synchronous generator.
    """

    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    async def put_items_in_queue():
        async for item in kani_stream:
            await queue.put(item)
        await queue.put(None)  # Sentinel to signal the end of the queue

    async def runner():
        await put_items_in_queue()

    def generator():
        asyncio.ensure_future(runner())

        while True:
            item = loop.run_until_complete(queue.get())
            if item is None:  # Check for the sentinel value
                break
            yield item

    return generator()


