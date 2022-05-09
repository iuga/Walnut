import click
from rich import print
from rich.panel import Panel


def log_info(msg: str = None, nl: bool = True) -> None:
    click.echo(f"• {msg} ", nl=nl)


def log_warning(msg: str = None) -> None:
    click.secho("⚠ Warning:", fg="yellow")
    click.secho(f"  {msg}", fg="yellow")


def log_error(msg: str = None, err: Exception = None) -> None:
    click.secho("✘ Error:", fg="red")
    click.secho(f"  {msg if msg else err}\n", fg="red")


def log_title(title: str) -> None:
    print(Panel.fit(f"[bold]{title}", border_style="bold"))
