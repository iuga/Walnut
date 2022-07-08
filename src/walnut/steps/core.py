from __future__ import annotations
import typing as t
from abc import ABC
from base64 import b64decode
from json import dumps, loads
from typing import Callable, Mapping, Sequence

from jinja2 import Environment
import click

from walnut.errors import StepExcecutionError
from walnut.messages import Message, ValueMessage, SequenceMessage, MappingMessage


class Step:
    """
    Step is a concrete implementation of a step that should be executed
    """

    templated: Sequence[str] = []

    def __init__(self, *, title: str = None, callbacks: list[Step] = None, **kwargs) -> None:
        self.title = title if title else str(self.__class__.__name__)
        self.callbacks = callbacks if callbacks else []
        self.jinja_env = Environment()

        def keys(d):
            d = loads(d)
            return dumps(list(d.keys()))

        self.jinja_env.filters["keys"] = keys

    def execute(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        """
        Excecutes the main logic of the step.
        The output of this execute() will be the input for the Next step on the Recipe/Chain
        Store is inmutable, no Step can change the content, except ExportToStoreStep()

        :raises StepExcecutionError if there was an error
        """
        self.render_templated({"inputs": inputs, "store": store})
        output = self.process(inputs, store)
        return output if isinstance(output, Message) else self.to_message(output)

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
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
        if isinstance(t, (list, t.Sequence)):
            return SequenceMessage(data)
        if isinstance(t, (dict, t.Mapping)):
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
        - `params.*` for Recipe parameters.

        While also the following filters "{{ settings.name | json }}":
        - `x | json` to get the result as a dictionary
        """
        for attr_name in self.templated:
            try:
                value = getattr(self, attr_name)
            except AttributeError:
                raise StepExcecutionError(
                    f"{attr_name!r} is configured as a templated field but {self} does not have this attribute."
                )
            if not value:
                continue
            # Currently, we do not support sequences of templates
            if isinstance(value, list):
                continue
            try:
                value = self.jinja_env.from_string(value).render(params)
                try:
                    # TODO: Convert to JSON if possible. We should parse the value and search for | json instead of this:
                    value = loads(value)
                except Exception:
                    # print(f"[warn] >> not able to json format the value {value}")
                    pass  # Nothing to do here...
                setattr(self, attr_name, value)
            except Exception as err:
                raise StepExcecutionError(f"Error rendering {attr_name}: {err}")

    def get_callbacks(self) -> list[Step]:
        return self.callbacks

    def print(self, name, v) -> None:
        print(f"[{name}]({type(v)}) >>>> {v}\n")


class StorageStep(ABC):
    """
    Abstract Step that indicates that child Steps will have access to a mutable Store.
    """
    pass


class DummyStep(Step):
    """
    DummyStep is a dummy implementation of a Step that only prints a message on the output
    """

    templated: Sequence[str] = tuple({"message"} | set(Step.templated))

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        return ValueMessage(self.message)


class StoreOutputStep(Step, StorageStep):
    """
    Stores the Step input into the Store variable.
    The content of input will be available for all next steps
    """

    def __init__(self, key: str, **kwargs):
        super().__init__(**kwargs)
        self.key = key

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        super().execute(inputs, store)
        store[self.key] = inputs
        return inputs


class DebugStep(Step):
    """
    DebugStep is a dummy implementation of a Step that only prints the parameters
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        data = {"inputs": inputs, "store": store}
        msg = dumps(data, indent=2).replace("\n", "\n   ")
        click.secho(f" ♦ Debug: {msg}", fg="magenta")
        return inputs


class LambdaStep(Step):
    """
    LambdaStep executes the provided function and return the output.
    Function signature:
        fn(Message, t.Dict[t.Any, t.Any]) -> Message
        where:
        - Message is the input data
        - Dict is the Recipe store
        and should return a Message that will be the input for the next step.
    """

    def __init__(self, fn: Callable[[Message, t.Dict[t.Any, t.Any]], Message], **kwargs):
        super().__init__(**kwargs)
        self.fn = fn

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        try:
            return self.fn(inputs, store)
        except Exception as ex:
            raise StepExcecutionError(f"error during lambda function call: {ex}")


class ReadFileStep(Step):
    """
    ReadFileStep reads the text file (txt, json, yaml, etc) and return the content in the
    selected key (default: "file").
    If template is defined, replace the keys of the dictionary with the values using the moustache format:
    name={{ name }} -> { "name": "Walnut" } -> name=Walnut
    """

    def __init__(self, filename: str, data: dict = {}, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename
        self.data = data

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if self.filename.endswith(".json"):
            m = self.read_json(self.data)
        else:
            m = self.read_raw(self.data)
        return m

    def read_raw(self, data: dict) -> Message:
        with open(self.filename, "r") as fp:
            c = fp.read()
            c = self.jinja_env.from_string(c).render(self.data)
            return ValueMessage(c)

    def read_json(self, data: dict) -> Message:
        m = self.read_raw(data)
        c = loads(m.get_value())
        return MappingMessage(c)


# class LoadParamsFromFileStep(ReadFileStep):
#     """
#     LoadParamsFromFileStep loads a dictionary from a file in order to be used as Recipe parameters or Step in the Recipe.
#     It subsets a given environment from the json that's why the settings.json file should follow the structure:
#     ```
#     {
#         "qa": {
#             "name": "qa",
#             ...
#         },
#         "prod": {
#             "name": "production",
#             ...
#         }
#     }
#     ```
#     In other words, if `env` is "prod", the settings entry will be:
#     ```
#     {
#         "store": {
#             "settings": {
#                 "name": "production",
#                 ...
#             }
#         }
#     }
#     ```
#     """
# 
#     templated: Sequence[str] = tuple({"env", "filename"} | set(Step.templated))
# 
#     def __init__(self, env: str = "dev", filename: str = "settings.json", key: str = None, **kwargs):
#         super().__init__(filename=filename, key=key, **kwargs)
#         self.env = env
# 
#     def execute(
#         self,
#         inputs: t.Dict[t.Any, t.Any],
#         store: t.Dict[t.Any, t.Any],
#     ) -> t.Dict[t.Any, t.Any]:
#         r = super().execute(inputs, store)
#         if self.env not in r[self.key]:
#             raise StepExcecutionError(f"environment {self.env} not found in settings")
#         if self.key:
#             r[self.key] = r[self.key][self.env]
#         else:
#             r = r[self.key][self.env]
#         return r
# 
# 
# class Base64DecodeStep(Step):
#     """
#     Decodes a Base64 string.
#     We decode the Base64 string into bytes of unencoded data.
#     We then convert the bytes-like object into a string using the provided encoding.
#     The decoded value is stored in {params}.{key}.
#     """
# 
#     templated: Sequence[str] = tuple({"value", "key"} | set(Step.templated))
# 
#     def __init__(self, value: str, key: str = "b64decoded", encoding="utf-8", **kwargs):
#         super().__init__(**kwargs)
#         self.value = value
#         self.key = key
#         self.encoding = encoding
# 
#     def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
#         r = super().execute(inputs, store)
#         r[self.key] = b64decode(self.value).decode(self.encoding)
#         return r
