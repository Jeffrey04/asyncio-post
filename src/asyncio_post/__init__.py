import typer

from .week1 import app as week1

app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(week1, name="week1")


def main() -> None:
    app()
