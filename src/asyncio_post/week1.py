import asyncio
import logging
import signal
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass

import httpx
import typer
from cytoolz.functoolz import thread_last
from prompt_toolkit import PromptSession

from asyncio_post.evaluator import evaluate
from asyncio_post.lexer import TOKENIZER, tokenize
from asyncio_post.parser import grammar, parse

app = typer.Typer(pretty_exceptions_enable=False)

logger = logging.getLogger(__name__)
logging.basicConfig()


@dataclass
class ShutdownHandler:
    signal: int | None = None

    async def __call__(self) -> None:
        logger.info("Shutting down tasks. signal:%s", self.signal or "")

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
        asyncio.create_task(self.shutdown_handler())


def welcome_text() -> Iterable[str]:
    return (
        "Welcome to Sample Application",
        "=============================",
        "",
        "Commands",
        "========",
        "dex <NUM>\t\t\tFetch pokemon <NUM> from pokedex",
        "dex-multi <NUM> [<NUM>, ...]\tFetch multiple pokemons from pokedex",
        "fib <NUM>\t\t\tFetch the <NUM>th fibonacci number",
        "job <NUM>\t\t\tShow the output for submitted job",
        "kill <NUM>\t\t\tKill the submitted job",
        "dash\t\t\t\tShow a summary of submitted tasks",
        "quit\t\t\t\tQuit this application",
        "",
    )


def init() -> None:
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        handler = ShutdownHandler(sig)

        loop.add_signal_handler(sig, lambda: asyncio.create_task(handler()))

    loop.set_exception_handler(ExceptionHandler(ShutdownHandler()))


async def repl() -> None:
    with suppress(asyncio.CancelledError):
        init()

        print("\n".join(welcome_text()))

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
                    (evaluate, client, tasks, ShutdownHandler()),
                ):
                    case asyncio.Task():
                        tasks.append((line, result))
                        print(f"Task {len(tasks)} is submitted")

                    case _:
                        print(result)


@app.callback(invoke_without_command=True)
def main() -> None:
    asyncio.run(repl())
