import asyncio
import logging
import multiprocessing
import signal
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from threading import Event
from types import FrameType

import httpx
from cytoolz.functoolz import thread_last
from prompt_toolkit import PromptSession
from typer import Typer

from asyncio_post.evaluator2 import evaluate
from asyncio_post.lexer import TOKENIZER, tokenize
from asyncio_post.parser import grammar, parse

app = Typer(pretty_exceptions_enable=False)

logger = logging.getLogger()
logging.basicConfig()


@dataclass
class ShutdownHandler:
    exit_event: Event
    signal: int | None = None

    async def __call__(self) -> None:
        logger.info("Shutting down tasks. signal:%s", self.signal or "")

        self.exit_event.set()

        tasks = tuple(
            task for task in asyncio.all_tasks() if task is not asyncio.current_task()
        )

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.get_running_loop().stop()


@dataclass
class ExceptionHandler:
    shutdown_handler: ShutdownHandler

    def __call__(self, loop, context) -> None:
        logger.error("Application failed. context:%s", context)
        asyncio.create_task(self.shutdown_handler())


def init(exit_event: Event) -> None:
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        handler = ShutdownHandler(exit_event, sig)

        loop.add_signal_handler(sig, lambda: asyncio.create_task(handler()))

    loop.set_exception_handler(ExceptionHandler(ShutdownHandler(exit_event)))


async def repl() -> None:
    with (
        ProcessPoolExecutor(max_workers=5) as executor,
        suppress(asyncio.CancelledError),
    ):
        manager = multiprocessing.Manager()
        exit_event = manager.Event()

        init(exit_event)

        t, g = TOKENIZER, grammar()
        session = PromptSession()

        tasks = []

        async with httpx.AsyncClient() as client:
            while True:
                line = await session.prompt_async("> ", handle_sigint=False)

                match result := await thread_last(
                    line,
                    (tokenize, t),
                    (parse, g),
                    (
                        evaluate,
                        client,
                        executor,
                        exit_event,
                        manager,
                        tasks,
                        ShutdownHandler(exit_event),
                    ),
                ):
                    case (_, asyncio.Future()):
                        tasks.append((line, *result))
                        print(f"Task {len(tasks)} is submitted")

                    case asyncio.Task():
                        tasks.append((line, None, result))
                        print(f"Task {len(tasks)} is submitted")

                    case _:
                        print(result)


@app.callback(invoke_without_command=True)
def main() -> None:
    asyncio.run(repl())
