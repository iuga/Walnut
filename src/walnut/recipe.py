from __future__ import annotations

import logging
import sys
import typing as t

import click

from walnut.errors import (
    RecipeExcecutionError,
    ShortCircuitError,
    StepAssertionError,
    StepExcecutionError,
    StepRequirementError,
    StepValidationError,
)
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.resources import Resources
from walnut.steps.core import Step
from walnut.storage import Storage
from walnut.ui import UI, NullRenderer, Renderer, StepRenderer

logger = logging.getLogger(__name__)


class StepContainer:
    """
    StepContainer is a base class that indicates an object that contains
    a list of steps.
    """

    steps = []

    def get_steps(self) -> list[Step]:
        return self.steps

    def add_step(self, step: Step):
        self.steps.append(step)


class IterableStepContainer(StepContainer):
    """
    IterableStepContainer is a base class that indicates an object that
    contains a sequence to iterate over a list of steps.
    """

    seq = []

    def get_sequence(self) -> list[t.Any]:
        return self.seq


class Section(Step, StepContainer):
    """
    Section is a Step that could contain a collection of Steps.
    It should be used to organize large executions of steps into different sections.
    """

    def __init__(self, steps: list[Step], title: str = None):
        self.title = title
        self.steps = steps


class Recipe(StepContainer):
    """
    Recipe is an ordered collection of steps that need to be prepared and executed/baked.
    During preparation you should load a parameters dictionary that will be used to
    configure the execution and business logic.
    All parameters (params) are available in the Storage for further usage via the
    templating system. E.g: {{ storage.params.x }}.
    You can also load and reuse Resources ( like database connections ) using DeclareResourceStep.
    Example:
    ```
    w.Recipe(
        title=f"Simple Walnut Demo v{__version__}",
        steps=[
            # List all your steps here...
        ],
    ).prepare(
        params=w.ReadFileStep(filename="settings.json", callbacks=[w.SelectStep(env)]),
    ).bake()
    ```
    """

    def __init__(self, title: str, steps: t.Sequence[Step]):
        self.title = title
        self.steps = steps
        self.traces = []
        self.storage = Storage()
        self.resources = Resources()
        self.executor = RecipeExecutor(self, ui=UI(file=sys.stdout))

    def bake(self) -> t.Any:
        """
        Bake is a cool syntax-sugar for a Recipe.
        It just call execute(...)
        """
        return self.execute().get_value()

    def prepare(self, params: t.Union[t.Dict[t.Any, t.Any], Step] = None) -> Recipe:
        """
        :params params is the complete configuration and parameters for the execution.
        """
        self.executor.prepare(params)
        return self

    def execute(self) -> Message:
        """
        Execute the recipe iterating over all steps in order.
        If one step fails, cancel the entire execution.
        :raises RecipeExcecutionError if there is any problem on a step
        """
        return self.executor.execute()

    def get_storage(self) -> Storage:
        """
        Recipe Storage is a central place to share information that are required ine more than one Step.
        You can use StoreOutputStep to add data.
        """
        return self.storage

    def get_resources(self) -> Resources:
        """
        Recipe Resources is a central place to share resources that are required in more than one Step.
        You can use DeclareResourceStep to define a resource. E.g: A database connection.
        """
        return self.resources

    def add_trace(self, trace: str, level: str = "info") -> None:
        """
        Add a tracing log to the recipe. It will be printed as extra information at the end of the top container. E.g:
         • Initializing the environment: ok
         └─► PostgreSQLResource db:postgresql:/tmp/my-socket:my-user:5432/my-database
        """
        self.traces.append({"level": level, "trace": trace})

    def get_title(self) -> str:
        return self.title

    def get_traces(self) -> t.List[t.Dict[str, str]]:
        return self.traces


class ForEachStep(Step, IterableStepContainer):
    """
    Execute the list of steps over each element of the Sequence.
    Sequence could be a list of elements and by default it's the input value.
    """

    templated: t.Sequence[str] = tuple({"seq"} | set(Step.templated))

    def __init__(
        self, steps: list[Step], seq: t.Union[str, list[t.Any], dict[str, t.Any]] = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.steps = steps

    def process(self, inputs: Message) -> Message:
        if not inputs and not self.seq:
            raise StepExcecutionError("ForEachStep: there are no elements to iterate")
        s = self.seq if self.seq is not None else inputs
        if isinstance(s, list):
            s = list(enumerate(s))
        if isinstance(s, SequenceMessage):
            s = list(enumerate(s.get_value()))
        if isinstance(s, dict):
            s = [(k, v) for k, v in s.items()]
        if isinstance(s, MappingMessage):
            s = [(k, v) for k, v in s.get_value().items()]
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


class RecipeExecutor:
    """
    Recipe Executor will prepare and execute (bake) a Recipe.
    We aim to separate structure from execution/ui.
    """

    def __init__(self, recipe: Recipe, ui: UI) -> None:
        self.recipe = recipe
        self.ready_to_bake = False
        self.ui = ui if ui else UI(file=sys.stdout)

    def prepare(self, params: t.Union[t.Dict[t.Any, t.Any], Step] = None):
        """
        Prepare the recipe for its execution.
        Parameters/Configurations are loaded during preparation
        They could be a Dictionary, a Step lo load a Map, or None (default to empty dictionary)
        """
        self.ui.title(self.recipe.get_title())
        params = params if params else {}
        if isinstance(params, Step):
            params = self.execute_steps([params], Message(), NullRenderer()).get_value()
        self.recipe.get_storage()["params"] = params
        self.ready_to_bake = True  # We are ready to bake the cake!

    def execute(self) -> Message:
        """
        Execute the recipe iterating over all steps in order.
        If one step fails, cancel the entire execution.
        :raises RecipeExcecutionError if there is any problem on a step
        """
        if not self.ready_to_bake:
            self.prepare()
        self.analize()
        output = Message()
        try:
            params = self.recipe.get_storage()["params"]
            output = self.execute_steps(self.recipe.steps, MappingMessage(params), renderer=None)
        except StepRequirementError:
            pass
        self.ui.echo("\nAll done! ✨ 🍰 ✨\n")
        return output

    def execute_steps(
        self,
        steps: t.Sequence[Step],
        inputs: Message,
        renderer: Renderer = None,
        parent: t.Optional[Step] = None,
        skip: bool = False,
    ) -> Message:
        """
        Execute a collection of steps, one step at a time in order.
        A collection of steps could be a Recipe or a Section.
        If during the execution we detect an StepAssertionError, we will "fail" the container execution, report
        the error anc continue with the next container. Only the first assertion error will be reported.
        """
        # For each step in the list:
        output = inputs
        short_circuit = skip
        for step in steps:
            # Execute the step or a collection of steps:
            if isinstance(step, IterableStepContainer):
                # Container: Iterate over a Collection of Steps
                if short_circuit:
                    continue
                seq = self.execute_step(step, output, NullRenderer(), skip=short_circuit)
                r = StepRenderer(step.get_title()).update() if not renderer else renderer
                for (n, v) in seq.get_value():
                    r = r.add_tag(n)
                    output = self.execute_steps(
                        step.get_steps(), ValueMessage(v), r, skip=short_circuit
                    )
                    r = r.remove_tag(n).update("ok", status=StepRenderer.STATUS_COMPLETE)
            elif isinstance(step, (StepContainer, PassthroughStep)):
                # Container: Collection of Steps
                r = StepRenderer(step.get_title()).update() if not renderer else renderer
                output = self.execute_steps(
                    step.get_steps(), output, r, parent=step, skip=short_circuit
                )
            else:
                # Step: Execute a single step
                r = (
                    StepRenderer(step.get_title()).update()
                    if not renderer
                    else renderer.update(step.get_title())
                )
                try:
                    passthrough = parent is not None and isinstance(parent, PassthroughStep)
                    out = self.execute_step(step, output, r, parent=parent, skip=short_circuit)
                    output = output if passthrough else out
                except (StepAssertionError):
                    # StepAssertionError mean that there is a data quality problem detected by Asserts.
                    # We should report and stop the current container execution and execute the next one.
                    return output
                except (ShortCircuitError):
                    short_circuit = True
        if len(steps) == 0 and renderer:
            renderer.update("ok", status=StepRenderer.STATUS_COMPLETE)
        self.log_traces()
        return output

    def execute_step(
        self,
        step: Step,
        inputs: Message,
        renderer: Renderer,
        level: int = 0,
        parent: t.Optional[Step] = None,
        skip: bool = False,
    ) -> Message:
        """
        Execute a single Step and its callbacks.
        This method is recursive, that's why we use level to manage the level we are. For example, only the highest level
        should log errors and failures ( or we will have duplicated messages )
        """
        output = inputs
        exception = None

        # Should we skip the execution of this task?
        if skip:
            renderer.update("skipped", status=StepRenderer.STATUS_SKIPPED)
            return output

        try:
            # Excecute the step and save the output as input for next step
            output = step.context(recipe=self.recipe).execute(output)
            # Step Callback Execution:
            callbacks = step.get_callbacks()
            if len(callbacks) > 0:
                for c in callbacks:
                    passthrough = isinstance(c, PassthroughStep)
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
                f"unexpected error executing the step {step.__class__.__name__}({step.get_title()}): {ex}"
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
                # ShortCircuitStep
                if isinstance(exception, ShortCircuitError):
                    renderer.update("ok", status=StepRenderer.STATUS_COMPLETE)
                    raise exception
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
        for step in self.recipe.get_steps():
            try:
                step.close()
            except Exception as err:
                raise RecipeExcecutionError(f"there was an error closing the recipe: {err}")

    def analize(self):
        """
        Return a brief analisys of the Recipe
        """
        ns, nc = self.count_steps(self.recipe.steps)
        title = click.style("Baking Recipe", bold=False, underline=True)
        nsp = click.style(ns if ns > 0 else "no", fg="magenta")
        ncp = click.style(nc if ns > 0 else "no", fg="magenta")
        self.ui.echo(
            f" {title} {ncp} section{'' if nc == 1 else 's'}, "
            f"{nsp} step{'' if ns == 1 else 's'}"
            "\n"
        )

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

    def log_traces(self) -> None:
        for td in self.recipe.get_traces():
            self.ui.echo(f" └─► {td['trace']}")
        self.recipe.get_traces().clear()
