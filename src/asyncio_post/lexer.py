from collections.abc import Callable, Iterable, Sequence
from enum import Enum, auto

from funcparserlib.lexer import Token, TokenSpec, make_tokenizer


class Spec(Enum):
    COMMAND = auto()
    NUMBER = auto()
    SPACE = auto()


type Tokenizer = Callable[[str], Iterable[Token]]

TOKENIZER: Tokenizer = make_tokenizer(
    (
        TokenSpec(Spec.COMMAND.name, r"[a-z][\w\-]+"),
        TokenSpec(Spec.NUMBER.name, r"\d+"),
        TokenSpec(Spec.SPACE.name, r"\s"),
    )
)


def tokenize(tokenizer: Tokenizer, line: str) -> Sequence[Token]:
    return tuple(token for token in tokenizer(line) if token.type != Spec.SPACE.name)
