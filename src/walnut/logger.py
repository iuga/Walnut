import click
from rich import print
from rich.panel import Panel


def log_info(msg: str = None, nl: bool = True) -> None:
    click.echo(f"• {msg} ", nl=nl)


def log_output(msg: str) -> None:
    msg = msg.replace("\n", "\n    ")
    click.secho("  > Output:")
    click.secho(f"    {msg}")


def log_warning(msg: str) -> None:
    click.secho("⚠ Warning:", fg="yellow")
    msg = msg.replace("\n", "\n  ")
    click.secho(f"  {msg}", fg="yellow")


def log_error(msg: str = None, err: Exception = None) -> None:
    click.secho("✘ Error:", fg="red")
    out = msg if msg else str(err)
    out = out.replace("\n", "\n  ")
    click.secho(f"  {out}\n", fg="red")


def log_title(title: str) -> None:
    print(Panel.fit(f"[bold]{title}", border_style="bold"))
