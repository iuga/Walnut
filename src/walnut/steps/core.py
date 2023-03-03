from __future__ import annotations

import re
import typing as t
from abc import ABC
from json import dumps, loads

from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

from walnut.errors import StepExcecutionError, StepRequirementError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage


class Step:
    """
    Step is a concrete implementation of a step that should be executed.
    """

    regex_tojson = re.compile(r".*\|.*tojson.*")
    templated: t.Sequence[str] = []

    def __init__(self, *, title: str = None, callbacks: list[Step] = None, **kwargs) -> None:
        self.title = title if title else str(self.__class__.__name__)
        self.callbacks = callbacks if callbacks else []
        self.ctx = {}
        self.jinja_env = Environment(undefined=StrictUndefined)
        self.templates = {}

        def keys(d):
            d = loads(d)
            return dumps(list(d.keys()))

        self.jinja_env.filters["keys"] = keys

    def execute(self, inputs: Message) -> Message:
        """
        Excecutes the main logic of the step.
        The output of this execute() will be the input for the Next step on the Recipe/Chain
        Store is inmutable, no Step can change the content, except ExportToStoreStep()

        :raises StepExcecutionError if there was an error
        """
        try:
            self.render_templated(
                {"inputs": inputs.get_value(), "storage": self.get_storage().as_dict()}
            )
            output = self.process(inputs)
            return output if isinstance(output, Message) else self.to_message(output)
        finally:
            self.restore_templated_values()

    def process(self, inputs: Message) -> Message:
        """
        process defines the main logic of the Step that should be executed.
        Concrete Steps should override process with its own code.
        """
        raise NotImplementedError("Base Step should never be called directly.")

    def to_message(self, data: t.Any) -> Message:
        """
        to_message tries to convert any type into a Message.
        If the type is not supported, return a base Message.
        """
        if isinstance(data, Message):
            return data
        if isinstance(data, (int, float, str, bool)):
            return ValueMessage(data)
        if isinstance(data, (list, t.Sequence)):
            return SequenceMessage(data)
        if isinstance(data, (dict, t.Mapping)):
            return MappingMessage(data)
        return Message(data)

    def close(self):
        """
        Close the asociated resources to this step
        :raises StepExcecutionError if there was an error
        """
        pass

    def render_templated(self, params: dict) -> None:
        """
        Templating is a powerful concept in Walnut to pass dynamic information into Steps instances at execution.
        For example, say you want to use a value from parameters as argument:

            LambdaStep(title="Executing: {{ params.settings.name }}")

        Will read from {params}.{settings}.{name} during execution. The output will be: "Executing: Some Name".
        The value in the double curly braces {{ }} is our templated code to be evaluated at runtime.

        Walnut leverages Jinja2, a templating framework in Python, as its templating engine.

        You have 3 input sources:
        - `inputs.*` for Step inputs.
        - `store.*` for Recipe store access.
        - `store.params.*` for Recipe parameters.

        While also the following filters "{{ settings.name | tojson }}":
        - `x | tojson` to get the result as a dictionary
        """
        # For each one of the step attributes that should be templated:
        for attr_name in self.templated:
            try:
                # Get the valus inside the variable ( the jinja template )
                value = getattr(self, attr_name)
                # Store the template value, we should restore it after execution
                self.templates[attr_name] = value
            except AttributeError:
                raise StepExcecutionError(
                    f"{attr_name!r} is configured as a templated field but {self} does not have this attribute."
                )
            if value:
                setattr(self, attr_name, self.render_value(value, params))

    def render_value(self, value, params: t.Dict) -> t.Any:
        """
        render_value is a recursive function that will try to render a list or dict value until we find a string that
        contains the final template. We also try to decode the rendered value as a JSON.
        """
        if isinstance(value, list):
            value = [self.render_value(v, params) for v in value]
        elif isinstance(value, dict):
            value = {
                self.render_value(k, params): self.render_value(v, params)
                for k, v in value.items()
            }
        else:
            exp = value
            value = self.render_string(value, params)  # Render the value using Jinja
            try:
                # If there is a json conversion, load the string into an object.
                if self.regex_tojson.match(exp) is not None:
                    value = loads(value)
            except Exception:
                pass  # Nothing to do here...
        return value

    def render_string(self, value: str, params: t.Dict) -> str:
        """
        Walnut leverages Jinja2, a templating framework in Python, as its templating engine.
        Loads a template from a string value, and return the rendered template as a string.
        """
        try:
            return self.jinja_env.from_string(value).render(params)
        except UndefinedError as err:
            raise StepRequirementError(f"{err} on template '{value}' with values {params}: {err}")
        except Exception as err:
            raise StepExcecutionError(f"Error rendering {value} with {params}: {err}")

    def restore_templated_values(self) -> None:
        """
        After the execution we should restore the templated values.
        When we are looping over a sequence, every iteration could have different values.
        E.g: "{inputs.val}" -> execute() -> "abc" -> finally() -> "{inputs.val}"
        """
        for key, value in self.templates.items():
            setattr(self, key, value)

    def context(self, recipe: t.Any = None) -> Step:
        """
        Set the context of this Step, like the Recipe executing it.
        """
        if recipe:
            self.ctx["recipe"] = recipe
        return self

    def get_storage(self):
        """
        Returns the Recipe storage
        """
        r = self.ctx.get("recipe")
        if not r:
            raise StepExcecutionError("Error getting the storage while the recipe is not set.")
        return r.get_storage()

    def get_resources(self):
        """
        Returns a resource with the given name or id.
        """
        r = self.ctx.get("recipe")
        if not r:
            raise StepExcecutionError("Error getting the resources while the recipe is not set.")
        return r.get_resources()

    def add_trace(self, trace: str, level: str = "info"):
        """
        Add a trace/log that should be printed into the Recipe execution:
        """
        r = self.ctx.get("recipe")
        if not r:
            raise StepExcecutionError("Error getting the resources while the recipe is not set.")
        r.add_trace(trace, level)

    def get_title(self) -> str:
        return self.title

    def __str__(self) -> str:
        return self.__class__.__name__

    def get_callbacks(self) -> list[Step]:
        return self.callbacks

    def print(self, name, v) -> None:
        print(f"[{name}]({type(v)}) >>>> {v}\n")

    def echo(self, msg: str, level: str = "info") -> None:
        """
        First Draft of the Step Logging functionality
        """
        pass

    def debug(self, msg: str) -> None:
        self.echo(msg, level="debug")

    def warning(self, msg: str) -> None:
        self.echo(msg, level="warn")

    def info(self, msg: str) -> None:
        self.echo(msg, level="info")

    def error(self, msg: str) -> None:
        self.echo(msg, level="error")


class StorageStep(ABC):
    """
    Abstract Step that indicates that child Steps will have access to a mutable Store.
    """

    pass
