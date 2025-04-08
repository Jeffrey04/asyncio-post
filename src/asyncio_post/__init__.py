import typer

from .week1 import app as week1
from .week2 import app as week2

app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(week1, name="week1")
app.add_typer(week2, name="week2")


def main() -> None:
    app()
