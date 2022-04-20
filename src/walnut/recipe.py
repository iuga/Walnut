import click
from walnut.steps import Step
from walnut.errors import StepExcecutionError, RecipeExcecutionError
from walnut.logger import log_info, log_error, log_title, log_warning


class Recipe:
    """
    Recipe is an ordered collection of steps that need to be executed.
    """

    steps = []

    def __init__(self, title: str, steps: list[Step]):
        self.title = title
        self.steps = steps

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
            response = {}
            exception = None
            status = click.style("ok", fg="green")
            try:
                log_info(step.title, nl=False)
                response = step.execute(params)
                response = response if response else {}
            except StepExcecutionError as err:
                exception = err
                status = click.style("error", fg="red")
                raise err
            except Exception as ex:
                exception = ex
                status = click.style("error", fg="red")
                raise RecipeExcecutionError(
                    f"unespected error executing the recipe: {ex}"
                )
            finally:
                click.echo(f"[{status}]")
                if exception is not None:
                    log_error(err=exception)
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
