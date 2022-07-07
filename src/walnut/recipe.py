import sys
import typing as t
from copy import deepcopy

import click

from walnut.errors import RecipeExcecutionError, StepAssertionError, StepExcecutionError
from walnut.steps.core import Step, StorageStep
from walnut.ui import UI, StepRenderer


class StepContainer:

    steps = []

    def get_steps(self) -> list[Step]:
        return self.steps

    def add_step(self, step: Step):
        self.steps.append(step)


class IterableStepContainer:

    seq = []
    steps = []

    def get_sequence(self) -> list[t.Any]:
        return self.seq

    def get_steps(self) -> list[Step]:
        return self.steps


class Recipe(StepContainer):
    """
    Recipe is an ordered collection of steps that need to be executed.
    """

    def __init__(self, title: str, steps: list[Step]):
        self.title = title
        self.steps = steps
        self.ui = UI(file=sys.stdout)
        self.store = {}

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
        params = params if params else {}
        if isinstance(params, Step):
            params = params.execute(inputs={}, store={})
        self.store["params"] = params
        self.ui.title(self.title)
        self.analize()
        output = self.execute_steps(self.steps, params, renderer=None)
        self.ui.echo("\nAll done! ✨ 🍰 ✨\n")
        return output

    def execute_steps(
        self, steps: list[Step], inputs: t.Dict[t.Any, t.Any], renderer: StepRenderer = None
    ) -> dict:
        """
        Execute a collection of steps, one step at a time in order.
        A collection of steps could be a Recipe or a Section.
        If during the execution we detect an StepAssertionError, we will "fail" the container execution, report
        the error anc continue with the next container. Only the first assertion error will be reported.
        """
        # For each step in the list:
        output = inputs
        for step in steps:
            # Execute the step or a collection of steps:
            if isinstance(step, IterableStepContainer):
                # Container: Iterate over a Collection of Steps
                for i in step.get_sequence():
                    r = StepRenderer(step.title).update() if not renderer else renderer
                    output = self.execute_steps(step.get_steps(), {"e": i}, r)
            elif isinstance(step, StepContainer):
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
                try:
                    output = self.execute_step(step, output, r)
                except StepAssertionError:
                    # StepAssertionError mean that there is a data quality problem detected by Asserts.
                    # We should report and stop the current container execution and execute the next one.
                    return output
        return output

    def execute_step(self, step: Step, inputs: t.Dict[t.Any, t.Any], renderer: StepRenderer, level: int = 0) -> t.Dict:
        """
        Execute a single Step and its callbacks.
        This method is recursive, that's why we use level to manage the level we are. For example, only the highest level
        should log errors and failures ( or we will have duplicated messages )
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
            output = step.execute(output, s)
            # Step Callback Execution:
            callbacks = step.get_callbacks()
            if len(callbacks) > 0:
                for c in callbacks:
                    output = self.execute_step(c, output, renderer, level=(level + 1))
                    output = output if output else {}
            output = output if output else {}
        except StepAssertionError as err:
            # StepAssertionError should be handled, but not reraised. An assertion error is quite expected and
            # we should report and continue.
            exception = err
        except StepExcecutionError as err:
            exception = err
            raise err
        except Exception as ex:
            exception = ex
            raise RecipeExcecutionError(f"unexpected error executing the step {step.__class__.__name__}({step.title}): {ex}")
        finally:
            if exception is None:
                renderer.update("ok", status=StepRenderer.STATUS_COMPLETE)
            else:
                if isinstance(exception, StepAssertionError) and level == 0:
                    renderer.update("fail", status=StepRenderer.STATUS_FAIL)
                    self.ui.failure(err=exception)  # Only high level container will log the failure.
                    raise exception  # We should raise to handle the container status
                if isinstance(exception, StepAssertionError):
                    renderer.update("fail", status=StepRenderer.STATUS_FAIL)
                    raise exception  # We should raise to handle the container status
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


class ForEachStep(Step, IterableStepContainer):
    """

    """
    def __init__(self, seq: t.Union[str, list[t.Any]], steps: list[Step], **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.steps = steps
