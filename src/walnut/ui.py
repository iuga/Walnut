from __future__ import annotations

import sys
import typing as t
from io import StringIO

import click


class UI:

    # TODO: What about light themes?
    COLOR_DEFAULT: str = "white"
    COLOR_ERROR: str = "bright_red"
    COLOR_SUCCESS: str = "bright_green"
    COLOR_PROCESSING: str = "bright_blue"
    COLOR_FAIL: str = "yellow"
    COLOR_SKIPPED: str = "bright_magenta"
    COLOR_WARNING: str = "yellow"

    BOX: t.Sequence[str] = ["╭", "─", "╮", "│", "╰", "╯"]

    def __init__(self, file: t.Optional[t.IO[t.Any]] = None):
        self.file = file if file else sys.stdout

    def title(self, title: str) -> UI:
        box = f"\n{self.BOX[0]}{self.BOX[1] * (len(title) + 2)}{self.BOX[2]}\n"
        box += f"{self.BOX[3]} {title} {self.BOX[3]}\n"
        box += f"{self.BOX[4]}{self.BOX[1] * (len(title) + 2)}{self.BOX[5]}\n"
        self.echo(box)
        return self

    def echo(self, message: t.Optional[t.Any] = None) -> UI:
        click.echo(message, file=self.file)
        return self

    def warning(self, message: t.Optional[t.Any] = None) -> UI:
        click.secho(" ╰─> ⚠ Warning:", fg=UI.COLOR_WARNING, file=self.file)
        click.secho(f"      {message}", fg=UI.COLOR_WARNING, file=self.file)
        return self

    def error(self, msg: str = None, err: Exception = None) -> UI:
        click.secho(" ╰─> ✘ Error:", fg=UI.COLOR_ERROR, file=self.file)
        click.secho(f"      {msg if msg else err}\n", fg=UI.COLOR_ERROR, file=self.file)
        return self

    def failure(self, msg: str = None, err: Exception = None) -> UI:
        click.secho(" ╰─> ⚠ Failure:", fg=UI.COLOR_FAIL, file=self.file)
        click.secho(f"      {msg if msg else err}\n", fg=UI.COLOR_FAIL, file=self.file)
        return self

    def move_up(self, lines: int = 1) -> UI:
        click.echo(f"\x1b[{lines}A", file=self.file, nl=False)
        return self

    def clear_line(self) -> UI:
        click.echo("\x1b[2K", file=self.file, nl=False)
        return self

    def update_last_echo(self, message: t.Optional[t.Any] = None) -> UI:
        # return self.echo(message)
        return self.move_up().clear_line().echo(message)


class Renderer:
    def update(self, update: t.Any = None, *, status: int = None) -> Renderer:
        raise NotImplementedError()

    def add_tag(self, tag: str) -> Renderer:
        return self

    def remove_tag(self, tag: str) -> Renderer:
        return self


class NullRenderer(Renderer):
    def update(self, update: t.Any = None, *, status: int = None) -> Renderer:
        return self

    def add_tag(self, tag: str) -> Renderer:
        return self

    def remove_tag(self, tag: str) -> Renderer:
        return self


class StepRenderer(Renderer):

    STATUS_IN_PROGRESS: int = 0
    STATUS_COMPLETE: int = 1
    STATUS_ERROR: int = 2
    STATUS_FAIL: int = 3
    STATUS_SKIPPED: int = 4
    STATUS_COLORS: dict[int, str] = {
        STATUS_IN_PROGRESS: UI.COLOR_PROCESSING,
        STATUS_ERROR: UI.COLOR_ERROR,
        STATUS_COMPLETE: UI.COLOR_SUCCESS,
        STATUS_FAIL: UI.COLOR_FAIL,
        STATUS_SKIPPED: UI.COLOR_SKIPPED,
    }

    def __init__(self, title: str, ui: UI = None) -> None:
        self.ui = ui if ui else UI()
        self.title = title
        self.rendered = False
        self.prefix = ""
        self.tags = []

    def update(self, update: t.Any = None, *, status: int = STATUS_IN_PROGRESS) -> StepRenderer:
        msg = self.message(update, status)
        if self.rendered:
            self.ui.update_last_echo(msg)
        else:
            self.ui.echo(msg)
            self.rendered = True
        return self

    def message(self, update: t.Any, status: int = STATUS_IN_PROGRESS) -> t.Any:
        state_color = self.STATUS_COLORS.get(status, "yellow")
        state = click.style("•", fg=state_color)
        msg = click.style(self.title, fg=UI.COLOR_DEFAULT)

        tags = ""
        for tag in self.tags:
            tags += f" ► {tag}"

        upd = ""
        if update:
            upd = ": {}".format(click.style(update, fg=state_color))
        return f" {state} {msg}{tags}{upd}"

    def add_tag(self, tag: str) -> StepRenderer:
        self.tags.append(tag)
        return self

    def remove_tag(self, tag: str) -> StepRenderer:
        self.tags.remove(tag)
        return self


class Capturing(list):
    """
    Capture the stdout and stderr streams of the current process and subprocesses.
    Usage:
    with Capturing(enabled=True) as output:
        r = self.process(inputs)

    with Capturing(output) as output:  # note the constructor argument
        print('hello world2')

    print(ouptut)
    """

    def __init__(self, enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.enabled = enabled

    def __enter__(self):
        if self.enabled:
            self._stdout = sys.stdout
            self._stderr = sys.stderr
            sys.stdout = self._outio = StringIO()
            sys.stderr = self._errio = StringIO()
        return self

    def __exit__(self, *args):
        if self.enabled:
            self.extend(self._outio.getvalue().splitlines())
            self.extend(self._errio.getvalue().splitlines())
            # free up some memory
            del self._outio
            del self._errio
            sys.stdout = self._stdout
            sys.stderr = self._stderr
