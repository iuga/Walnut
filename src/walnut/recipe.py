from __future__ import annotations

import logging
import sys
import typing as t
from copy import deepcopy

import click

from walnut.errors import (
    RecipeExcecutionError,
    StepAssertionError,
    StepExcecutionError,
    StepRequirementError,
    StepValidationError,
)
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.resources import Resource, ResourceFactory
from walnut.steps.core import Step, StorageStep
from walnut.ui import UI, NullRenderer, Renderer, StepRenderer

logger = logging.getLogger(__name__)


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
        self.resources = {}
        self.verbose = False

    def bake(
        self,
        params: t.Union[t.Dict[t.Any, t.Any], Step] = None,
        resources: t.Union[t.Dict[t.Any, t.Any], Step] = None,
        verbose: bool = False,
    ) -> t.Any:
        """
        Bake is a cool syntax-sugar for a Recipe.
        It just call execute(...)
        """
        return self.execute(params=params, resources=resources, verbose=verbose).get_value()

    def execute(
        self,
        params: t.Union[t.Dict[t.Any, t.Any], Step] = None,
        resources: t.Union[t.Dict[t.Any, t.Any], Step] = None,
        verbose: bool = False,
    ) -> Message:
        """
        Execute the recipe iterating over all steps in order.
        If one step fails, cancel the entire execution.
        :raises RecipeExcecutionError if there is any problem on a step
        """
        self.verbose = verbose
        # Params could be a Dictionary or a Step or None
        params = params if params else {}
        if isinstance(params, Step):
            params = self.execute_steps([params], Message(), NullRenderer()).get_value()
        # Resources could be a Dictionary or a Step or None
        resources = resources if resources else {}
        if isinstance(resources, Step):
            resources = self.execute_steps([resources], Message(), NullRenderer()).get_value()
        self.load_resources(resources)
        self.store["params"] = params
        self.ui.title(self.title)
        self.analize()
        # TODO: I really dont like this...
        output = Message()
        try:
            output = self.execute_steps(self.steps, MappingMessage(params), renderer=None)
        except StepRequirementError:
            pass
        self.ui.echo("\nAll done! ✨ 🍰 ✨\n")
        return output

    def execute_steps(
        self,
        steps: list[Step],
        inputs: Message,
        renderer: Renderer = None,
        parent: t.Optional[Step] = None,
    ) -> Message:
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
                seq = self.execute_step(step, output, NullRenderer())
                for i in seq.get_value():
                    r = StepRenderer(step.title).update() if not renderer else renderer
                    output = self.execute_steps(step.get_steps(), ValueMessage(i), r)
            elif isinstance(step, (StepContainer, PassthroughStep)):
                # Container: Collection of Steps
                r = StepRenderer(step.title).update() if not renderer else renderer
                output = self.execute_steps(step.get_steps(), output, r, parent=step)
            else:
                # Step: Execute a single step
                r = (
                    StepRenderer(step.title).update()
                    if not renderer
                    else renderer.update(step.title)
                )
                try:
                    passthrough = parent is not None and isinstance(parent, PassthroughStep)
                    r = self.execute_step(step, output, r, parent=parent)
                    output = output if passthrough else r
                except (StepAssertionError):
                    # StepAssertionError mean that there is a data quality problem detected by Asserts.
                    # We should report and stop the current container execution and execute the next one.
                    return output
        return output

    def execute_step(
        self,
        step: Step,
        inputs: Message,
        renderer: Renderer,
        level: int = 0,
        parent: t.Optional[Step] = None,
    ) -> Message:
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
            self.echo(f"executing step: {step} with inputs: {output}")
            output = step.context(recipe=self).execute(output, s)
            # Step Callback Execution:
            callbacks = step.get_callbacks()
            if len(callbacks) > 0:
                for c in callbacks:
                    passthrough = isinstance(c, PassthroughStep)
                    self.echo(
                        f"executing callback {parent if parent else 'root'} ► {step} ► {c.__class__.__name__} with {'passthrough ' if passthrough else ''}inputs: {output}\n"
                    )
                    if isinstance(c, (StepContainer, PassthroughStep)):
                        r = self.execute_steps(c.get_steps(), output, renderer, parent=c)
                    else:
                        r = self.execute_step(
                            c, output, renderer, level=(level + 1), parent=parent
                        )
                    r = r if r else Message()
                    output = output if passthrough else r
            output = output if output else Message()
        except StepAssertionError as err:
            # StepAssertionError should be handled, but not reraised.
            # An assertion error is quite expected and we should report and continue.
            err.add(step)
            exception = err
        except StepRequirementError as err:
            err.add(step)
            exception = err
            raise err
        except StepValidationError as err:
            exception = err
            raise err
        except StepExcecutionError as err:
            exception = err
            raise err
        except Exception as ex:
            exception = ex
            raise RecipeExcecutionError(
                f"unexpected error executing the step {step.__class__.__name__}({step.title}): {ex}"
            )
        finally:
            if exception is None:
                renderer.update("ok", status=StepRenderer.STATUS_COMPLETE)
            else:
                if isinstance(exception, StepAssertionError) and level == 0:
                    renderer.update("fail", status=StepRenderer.STATUS_FAIL)
                    # Only high level container will log the failure.
                    self.ui.failure(err=exception)
                    # TODO: Do we need this reraise?
                    raise exception  # We should raise to handle the container status
                if isinstance(exception, StepAssertionError):
                    renderer.update("fail", status=StepRenderer.STATUS_FAIL)
                    raise exception  # We should raise to handle the container status
                if isinstance(exception, StepRequirementError) and level == 0:
                    renderer.update("error", status=StepRenderer.STATUS_ERROR)
                    # Only high level container will log the failure.
                    self.ui.error(err=exception)
                    raise exception  # We should raise to handle the container status
                if isinstance(exception, StepRequirementError):
                    renderer.update("error", status=StepRenderer.STATUS_ERROR)
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
        ns, nc = self.count_steps(self.steps)
        nr = len(self.resources)
        title = click.style(" Recipe operations", bold=True)
        nsp = click.style(ns if ns > 0 else "no", fg="magenta")
        ncp = click.style(nc if ns > 0 else "no", fg="magenta")
        nrp = click.style(nr if nr > 0 else "no", fg="magenta")
        self.ui.echo(
            f"{title}: {ncp} section{'' if nc == 1 else 's'}, "
            f"{nsp} step{'' if ns == 1 else 's'}, "
            f"{nrp} resource{'' if nr == 1 else 's'}"
        )
        self.ui.echo()

    def count_steps(self, steps) -> t.Tuple[int, int]:
        ns = 0
        nc = 0
        for s in steps:
            ns += 1
            if isinstance(s, StepContainer):
                nc += 1
                nsi, nci = self.count_steps(s.get_steps())
                ns += nsi
                nc += nci
            else:
                callbacs = s.get_callbacks()
                if len(callbacs) > 0:
                    nsi, nci = self.count_steps(callbacs)
                    ns += nsi
                    nc += nci
        return (ns, nc)

    def echo(self, message):
        if self.verbose:
            print(">>", message)
            logger.info(message)

    def load_resources(self, resources: t.Dict) -> None:
        """
        Get a dictionary with the Resource definition and load the Resources.
        """
        for n, r in resources.items():
            if "engine" not in r:
                raise RecipeExcecutionError(
                    f"resouce {n} does not have the required 'engine' entry."
                    "available engines: {ResourceFactory.RESOURCES.keys()}"
                )
            engine = r["engine"]
            del r["engine"]
            self.resources[n] = ResourceFactory.create(engine, **r)

    def get_resource(self, resource_id: str) -> Resource:
        """
        Return a Resource with the given ID.
        """
        if resource_id not in self.resources:
            raise StepExcecutionError(
                f"Resource '{resource_id}' not defined in Recipe. "
                "Please add it to the Recipe().bake(resources={...})."
                f"Available resources: {','.join(self.resources.keys())}"
            )
        return self.resources[resource_id]


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
    Execute the list of steps over each element of the Sequence.
    Sequence could be a list of elements and by default it's the input value.
    """

    templated: t.Sequence[str] = tuple({"seq"} | set(Step.templated))

    def __init__(self, steps: list[Step], seq: t.Union[str, list[t.Any]] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.steps = steps

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if not inputs and not self.seq:
            raise StepExcecutionError("ForEachStep: there are no elements to iterate")
        s = self.seq if self.seq is not None else inputs
        if isinstance(s, SequenceMessage):
            s = s.get_value()
        if not isinstance(s, (list, t.Sequence)):
            raise StepExcecutionError(f"ForEachStep: the input is not iterable: {s}")
        if len(s) == 0:
            raise StepExcecutionError("ForEachStep: the input sequence is empty")
        return SequenceMessage(s)


class PassthroughStep(Step, StepContainer):
    """
    PassthroughStep contain a sequence of steps where the input should pass through the entire sequence.
    inputs -> Sequence[Step, Step, Step] -> inputs
    This abstract step is designed when we should execute several operations over the same input.
    """

    def __init__(self, steps: list[Step], title: str = None):
        self.title = title
        self.steps = steps
