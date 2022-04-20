import click


def log_info(msg: str = None, nl: bool = True) -> None:
    click.echo(f"• {msg} ", nl=nl)


def log_warning(msg: str = None) -> None:
    click.echo(click.style("! Warning:", fg="yellow"))
    click.echo(click.style(f"  {msg}", fg="yellow"))


def log_error(msg: str = None, err: Exception = None) -> None:
    click.echo(click.style("✘ Error:", fg="red"))
    click.echo(click.style(f"  {msg if msg else err}\n", fg="red"))


def log_title(title: str) -> None:
    n = len(title)
    click.echo("-" * (n + 4))
    click.echo(f"  {click.style(title, bold=True)}  ")
    click.echo("-" * (n + 4))
