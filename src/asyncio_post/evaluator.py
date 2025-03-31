import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Sequence

import httpx

from asyncio_post.commands import dex, dex_multi, fib
from asyncio_post.parser import Command, Expression


async def evaluate(
    client: httpx.AsyncClient,
    tasks: Sequence[tuple[str, asyncio.Task[str]]],
    shutdown_handler: Callable[..., Coroutine[None, None, None]],
    expression: Expression,
) -> Awaitable[str] | str:
    match expression:
        case Expression(command=Command.DEX):
            return asyncio.create_task(dex(client, expression.args[0]))

        case Expression(command=Command.DEX_MULTI):
            return asyncio.create_task(dex_multi(client, *expression.args))

        case Expression(command=Command.FIB):
            return asyncio.create_task(asyncio.to_thread(fib, expression.args[0]))

        case Expression(command=Command.JOB):
            return job(tasks[expression.args[0] - 1])

        case Expression(command=Command.KILL):
            return kill(tasks[expression.args[0]] - 1)

        case Expression(command=Command.DASH):
            return dash(tasks)

        case Expression(command=Command.QUIT):
            return quit(shutdown_handler)

        case _:
            raise Exception("Unknown command")


def kill(task: tuple[str, asyncio.Task[str]]) -> str:
    task[-1].cancel()

    return f'Task "{task[0]}" is killed'


def quit(shutdown_handler: Callable[..., Coroutine[None, None, None]]) -> str:
    asyncio.create_task(shutdown_handler())

    return "Exiting"


def job(task: tuple[str, asyncio.Task[str]]) -> str:
    try:
        return task[-1].result()
    except asyncio.InvalidStateError:
        return "Still waiting"


def dash(tasks: Sequence[tuple[str, asyncio.Task[str]]]) -> str:
    result = [
        "\t".join(("id", f"{'command':16s}", "done?", "result")),
        "\t".join(("==", f"{'=' * 16}", "=====", "======")),
    ]

    for num, (line, task) in enumerate(tasks, 1):
        result.append(
            "\t".join(
                (
                    str(num),
                    f"{line:16s}",
                    str(task.done()),
                    task.done() and str(task.result())[:16] or "",
                )
            )
        )

    return "\n".join(result)
