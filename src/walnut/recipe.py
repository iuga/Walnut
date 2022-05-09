import click
from walnut.steps import Step
from walnut.errors import StepExcecutionError, RecipeExcecutionError
from walnut.logger import log_info, log_error, log_title, log_warning, log_output
from rich.console import Console
from rich.text import Text


class Recipe:
    """
    Recipe is an ordered collection of steps that need to be executed.
    """

    steps = []

    def __init__(self, title: str, steps: list[Step]):
        self.title = title
        self.steps = steps
        self.console = Console(log_time=False)

    def bake(self, params: dict = {}) -> dict:
        """
        Bake is a cool syntax-sugar for a Recipe.
        It just call execute(...)
        """
        return self.execute(params)

    def execute(self, params: dict = {}) -> dict:
        """
        Execute the recipe iterating over all steps in order.
        If one step fails, cancel the entire execution.
        :raises RecipeExcecutionError if there is any problem on a step
        """
        context = params
        log_title(self.title)
        for step in self.steps:
            with self.console.status(f"{step.title} ", spinner_style="white") as status:
                response = {}
                exception = None
                success = True
                try:
                    response = step.execute(params)
                    response = response if response else {}
                except StepExcecutionError as err:
                    exception = err
                    success = False
                    raise err
                except Exception as ex:
                    exception = ex
                    success = False
                    raise RecipeExcecutionError(
                        f"unespected error executing the recipe: {ex}"
                    )
                finally:
                    status.stop()
                    text = Text()
                    text.append(f"• {step.title}")
                    text.append(" [")
                    text.append(
                        f"{'ok' if success else 'error'}",
                        style="green" if success else "red",
                    )
                    text.append("]")
                    self.console.print(text)
                    # TODO: Errors should have the same behaviour as warnings?
                    if exception is not None:
                        click.echo("")
                        log_error(err=exception)
                    if "stdout" in response:
                        click.echo("")
                        log_output(response["stdout"])
                        del response["stdout"]
                    context.update(response)
                    self.close()

        log_info("All done! ✨ 🍰 ✨")

        if "warnings" in context:
            click.echo("")
            for w in context["warnings"]:
                log_warning(w)
            click.echo("")

        return context

    def close(self):
        """
        close all the resources iterating over all steps in order of execution
        """
        for step in self.steps:
            try:
                step.close()
            except Exception as err:
                raise RecipeExcecutionError(
                    f"there was an error closing the recipe: {err}"
                )

    def get_steps(self) -> list:
        """
        Get all steps from this recipe
        """
        return self.steps

    def add_step(self, step: Step):
        """
        Add a new step at the end of the recipe
        """
        self.steps.append(step)
