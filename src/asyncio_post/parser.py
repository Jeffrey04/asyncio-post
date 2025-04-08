from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from funcparserlib.parser import Parser, finished, many
from funcparserlib.parser import tok as tok_

from asyncio_post.lexer import Spec, Token


class Command(Enum):
    DEX = auto()
    DEX_MULTI = auto()
    FIB = auto()
    FIB_MULTI = auto()
    JOB = auto()
    KILL = auto()
    DASH = auto()
    QUIT = auto()


@dataclass
class Expression:
    command: Command
    args: Sequence[Any]


def tok(spec: Spec, *args: Any, **kwargs: Any) -> Parser[Token, str]:
    return tok_(spec.name, *args, **kwargs)


def grammar() -> Parser[Token, Expression]:
    number = tok(Spec.NUMBER) >> int

    dex = tok(Spec.COMMAND, "dex") + number >> (
        lambda elem: Expression(Command.DEX, (elem[1],))
    )
    dex_multi = tok(Spec.COMMAND, "dex-multi") + many(number) >> (
        lambda elem: Expression(Command.DEX_MULTI, elem[1])
    )
    fib = tok(Spec.COMMAND, "fib") + number >> (
        lambda elem: Expression(Command.FIB, (elem[1],))
    )
    fib_multi = tok(Spec.COMMAND, "fib-multi") + many(number) >> (
        lambda elem: Expression(Command.FIB_MULTI, elem[1])
    )
    job = tok(Spec.COMMAND, "job") + number >> (
        lambda elem: Expression(Command.JOB, (elem[1],))
    )
    kill = tok(Spec.COMMAND, "kill") + number >> (
        lambda elem: Expression(Command.KILL, (elem[1],))
    )
    dash = tok(Spec.COMMAND, "dash") >> (lambda _: Expression(Command.DASH, ()))
    quit = tok(Spec.COMMAND, "quit") >> (lambda _: Expression(Command.QUIT, ()))

    expression = dex | dex_multi | fib | fib_multi | job | kill | dash | quit

    return expression + finished >> (lambda elem: elem[0])


def parse(grammar: Parser[Token, Expression], tokens: Iterable[Token]) -> Expression:
    return grammar.parse(tuple(tokens))
