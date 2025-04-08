import asyncio
import logging
import time
from itertools import count
from threading import Event

import httpx
from cytoolz.functoolz import memoize

logger = logging.getLogger()
logging.basicConfig()


async def dex(client: httpx.AsyncClient, id: int) -> str:
    assert isinstance(id, int)
    response = await client.get(f"https://pokeapi.co/api/v2/pokemon/{id}/")

    return f"The pokemon with id {id} is {response.json()['name']}"


async def dex_multi(client: httpx.AsyncClient, *ids: int) -> str:
    try:
        result = []

        for id in ids:
            result.append(await dex(client, id))

            await asyncio.sleep(10)

        return "\n".join(result)
    except asyncio.CancelledError:
        logger.info("cancelling")


def fib(
    nth: int, exit_event: Event | None = None, cancel_event: Event | None = None
) -> str:
    assert isinstance(nth, int) and nth > 0

    result = ()

    for i in range(1, nth + 1):
        if (exit_event and exit_event.is_set()) or (
            cancel_event and cancel_event.is_set()
        ):
            return "Cancelled"

        match i:
            case 1:
                result = (0,)

            case 2:
                result += (1,)

            case _:
                result = result[1:] + (sum(result),)

    assert len(result) > 0

    return f"The {nth}th fibonacci number is {result[-1]}"