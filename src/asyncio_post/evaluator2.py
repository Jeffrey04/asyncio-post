import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Sequence
from concurrent.futures import ProcessPoolExecutor
from multiprocessing.managers import SyncManager
from threading import Event

import httpx

from asyncio_post.commands import dex, fib
from asyncio_post.parser import Command, Expression


async def evaluate(
    client: httpx.AsyncClient,
    executor: ProcessPoolExecutor,
    exit_event: Event,
    manager: SyncManager,
    tasks: Sequence[
        tuple[
            str,
            Event | None,
            asyncio.Task[str] | asyncio.Future[str] | asyncio.Future[list[str]],
        ]
    ],
    shutdown_handler: Callable[..., Coroutine[None, None, None]],
    expression: Expression,
) -> (
    asyncio.Task[str]
    | tuple[Event, asyncio.Future[str]]
    | tuple[Event, asyncio.Future[list[str]]]
    | str
):
    match expression:
        case Expression(command=Command.DEX):
            return asyncio.create_task(dex(client, expression.args[0]))

        case Expression(command=Command.FIB):
            cancel_event = manager.Event()
            return cancel_event, asyncio.get_running_loop().run_in_executor(
                executor, fib, expression.args[0], exit_event, cancel_event
            )

        case Expression(command=Command.FIB_MULTI):
            cancel_event = manager.Event()
            return cancel_event, asyncio.gather(
                *[
                    asyncio.get_running_loop().run_in_executor(
                        executor, fib, nth, exit_event, cancel_event
                    )
                    for nth in expression.args
                ]
            )

        case Expression(command=Command.JOB):
            return job(tasks[expression.args[0] - 1])

        case Expression(command=Command.KILL):
            return kill(tasks[expression.args[0] - 1])

        case Expression(command=Command.DASH):
            return dash(tasks)

        case Expression(command=Command.QUIT):
            return quit(shutdown_handler)

        case _:
            raise Exception("Unknown command")


def kill(
    task: tuple[str, Event | None, asyncio.Task[str] | Awaitable[str]],
) -> str:
    match task[-1]:
        case asyncio.Task():
            task[-1].cancel()

        case asyncio.Future():
            assert task[1]

            task[1].set()

    return f'Task "{task[0]}" is killed'


def quit(shutdown_handler: Callable[..., Coroutine[None, None, None]]) -> str:
    asyncio.create_task(shutdown_handler())

    return "Exiting"


def job(
    task: tuple[
        str,
        Event | None,
        asyncio.Task[str] | asyncio.Future[str] | asyncio.Future[list[str]],
    ],
) -> str:
    try:
        match task[-1]:
            case asyncio.Future():
                return (
                    "; ".join(task[-1].result())
                    if isinstance(task[-1].result(), list)
                    else task[-1].result()
                )  # type: ignore

            case _:
                return "Still waiting"

    except asyncio.InvalidStateError:
        return "Still waiting"


def dash(
    tasks: Sequence[
        tuple[
            str,
            Event | None,
            asyncio.Task[str] | asyncio.Future[str] | asyncio.Future[list[str]],
        ]
    ],
) -> str:
    result = [
        "\t".join(("id", f"{'command':16s}", "done?", "result")),
        "\t".join(("==", f"{'=' * 16}", "=====", "======")),
    ]

    for num, (line, _, task) in enumerate(tasks, 1):
        task_done, task_result = False, None

        if task_done := task.done():
            task_result = (
                "; ".join(task.result())
                if isinstance(task.result(), list)
                else task.result()
            )

        result.append(
            "\t".join(
                (
                    str(num),
                    f"{line:16s}",
                    str(task_done),
                    task_done and str(task_result)[:16] or "",
                )
            )
        )

    return "\n".join(result)
