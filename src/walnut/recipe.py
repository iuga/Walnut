import sys
import typing as t
from copy import deepcopy

import click

from walnut.errors import RecipeExcecutionError, StepExcecutionError
from walnut.steps.core import Step, StorageStep
from walnut.ui import UI, StepRenderer


class StepContainer:

    steps = []

    def get_steps(self) -> list[Step]:
        return self.steps

    def add_step(self, step: Step):
        self.steps.append(step)


class Recipe(StepContainer):
    """
    Recipe is an ordered collection of steps that need to be executed.
    """

    def __init__(self, title: str, steps: list[Step]):
        self.title = title
        self.steps = steps
        self.ui = UI(file=sys.stdout)
        self.store = {}
        self.params = {}

    def bake(self, params: t.Union[t.Dict[t.Any, t.Any], Step] = None) -> dict:
        """
        Bake is a cool syntax-sugar for a Recipe.
        It just call execute(...)
        """
        return self.execute(params)

    def execute(self, params: t.Union[t.Dict[t.Any, t.Any], Step] = None) -> dict:
        """
        Execute the recipe iterating over all steps in order.
        If one step fails, cancel the entire execution.
        :raises RecipeExcecutionError if there is any problem on a step
        """
        # Params could be a Dictionary or a Step or None
        self.params = params if params else {}
        if isinstance(self.params, Step):
            self.params = self.params.execute(inputs={}, store={}, params={})
        self.ui.title(self.title)
        self.analize()
        output = self.execute_steps(self.steps, self.params, renderer=None)
        self.ui.echo("\nAll done! ✨ 🍰 ✨\n")
        return output

    def execute_steps(
        self, steps: list[Step], inputs: t.Dict[t.Any, t.Any], renderer: StepRenderer = None
    ) -> dict:
        """
        Execute a collection of steps, one step at a time in order.
        """
        # For each step in the list:
        output = {}
        for step in steps:
            # Execute the step or a collection of steps:
            if isinstance(step, StepContainer):
                # Container: Collection of Steps
                r = StepRenderer(step.title).update() if not renderer else renderer
                output = self.execute_steps(step.get_steps(), output, r)
            else:
                # Step: Execute a single step
                r = (
                    StepRenderer(step.title).update()
                    if not renderer
                    else renderer.update(step.title)
                )
                output = self.execute_step(step, output, r)
        return output

    def execute_step(
        self, step: Step, inputs: t.Dict[t.Any, t.Any], renderer: StepRenderer
    ) -> dict:
        """
        Execute a single Step
        """
        output = inputs
        exception = None
        try:
            # Steps only have access to a ready-only copy of store.
            # However, some Steps can update and save information in store
            s = self.store
            if not isinstance(step, StorageStep):
                s = deepcopy(self.store)
            # Excecute the step and save the output as input for next step
            output = step.execute(output, s, self.params)
            output = output if output else {}
        except StepExcecutionError as err:
            exception = err
            raise err
        except Exception as ex:
            exception = ex
            raise RecipeExcecutionError(f"unespected error executing the recipe: {ex}")
        finally:
            if exception is None:
                renderer.update("ok", status=StepRenderer.STATUS_COMPLETE)
            else:
                renderer.update("error", status=StepRenderer.STATUS_ERROR)
                self.ui.error(err=exception)
            self.close()
        return output

    def close(self):
        """
        close all the resources iterating over all steps in order of execution
        """
        for step in self.steps:
            try:
                step.close()
            except Exception as err:
                raise RecipeExcecutionError(f"there was an error closing the recipe: {err}")

    def analize(self):
        """
        Return a brief analisys of the Recipe
        """
        ns = 0
        nc = 1
        for s in self.steps:
            if isinstance(s, StepContainer):
                nc += 1
                ns += len(s.get_steps())
            ns += 1
        title = click.style(" Recipe operations", bold=True)
        ns = click.style(ns, fg="magenta")
        nc = click.style(nc, fg="magenta")
        self.ui.echo(f"{title}: {nc} sections, {ns} steps")
        self.ui.echo()


class Section(Step, StepContainer):
    """
    Section is a Step that could contain a collection of Steps.
    It should be used to organize large executions of steps into different sections.
    """

    def __init__(self, steps: list[Step], title: str = None):
        self.title = title
        self.steps = steps
