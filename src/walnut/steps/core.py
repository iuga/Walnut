import typing as t
from abc import ABC
from base64 import b64decode
from json import dumps, loads
from typing import Callable, Sequence

from jinja2 import Environment
import chevron
import click

from walnut.errors import StepExcecutionError


class Step:
    """
    Step is a concrete implementation of a step that should be executed
    """

    templated: Sequence[str] = []

    def __init__(self, *, title: str = None):
        self.title = title if title else str(self.__class__.__name__)
        self.jinja_env = Environment()

        def keys(d):
            d = loads(d)
            return dumps(list(d.keys()))

        self.jinja_env.filters["keys"] = keys

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        """
        The output of this execute() will be the input for the Next step on the Recipe/Chain
        Store is inmutable, no Step can change the content, except ExportToStoreStep()
        Params are only the Recipe Parameters and other extra things like execution_date.
        Templated fields will be a conbination of {store:{}, params:{}, inputs:{}}

        Excecute the main logic of the step
        :raises StepExcecutionError if there was an error
        """
        self.render_templated(
            {
                "inputs": inputs,
                "store": store,
            }
        )
        return {}

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

    def __init__(self, *, message: str):
        super().__init__()
        self.message = message

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        r["message"] = self.message
        return r


class StoreOutputStep(Step, StorageStep):
    """
    Stores the Step input into the Store variable.
    The content of input will be available for all next steps
    """

    def __init__(self, key: str = None):
        super().__init__()
        self.key = key

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        super().execute(inputs, store)
        if self.key is not None:
            store[self.key] = inputs
        else:
            store.update(inputs)
        return inputs


class DebugStep(Step):
    """
    DebugStep is a dummy implementation of a Step that only prints the parameters
    """

    def __init__(self):
        super().__init__(title="Debugging context")

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        super().execute(inputs, store)
        msg = dumps({"inputs": inputs, "store": store}, indent=2).replace(
            "\n", "\n   "
        )
        click.secho(f" ♦ Debug: {msg}", fg="magenta")
        return inputs


class LambdaStep(Step):
    """
    LambdaStep executes the provided function
    """

    def __init__(self, fn: Callable[[t.Dict, t.Dict], t.Dict], title: str = None):
        super().__init__(title=title)
        self.fn = fn

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        super().execute(inputs, store)
        try:
            return self.fn(inputs, store)
        except Exception as ex:
            raise StepExcecutionError(f"error during function call: {ex}")


class ReadFileStep(Step):
    """
    ReadFileStep reads the text file (txt, json, yaml, etc) and return the content in the
    selected key (default: "file").
    If template is defined, replace the keys of the dictionary with the values using the moustache format:
    name={{ name }} -> { "name": "Walnut" } -> name=Walnut
    Also, it support all the Recipe parameters using the "params." prefix:
    params={"env": "qa"} -> {{ params.env }} -> qa
    """

    def __init__(self, filename: str, key: str = None, data: dict = {}, title: str = None):
        super().__init__(title=title)
        self.key = key
        self.filename = filename
        self.data = data

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        if self.filename.endswith(".json"):
            r[self.key] = self.read_json(self.data)
        else:
            r[self.key] = self.read_raw(self.data)
        return r

    def read_raw(self, data: dict) -> str:
        with open(self.filename, "r") as fp:
            return str(chevron.render(fp, data))

    def read_json(self, data: dict) -> dict:
        return loads(self.read_raw(data))


class LoadParamsFromFileStep(ReadFileStep):
    """
    LoadParamsFromFileStep loads a dictionary from a file in order to be used as Recipe parameters or Step in the Recipe.
    It subsets a given environment from the json that's why the settings.json file should follow the structure:
    ```
    {
        "qa": {
            "name": "qa",
            ...
        },
        "prod": {
            "name": "production",
            ...
        }
    }
    ```
    In other words, if `env` is "prod", the settings entry will be:
    ```
    {
        "store": {
            "settings": {
                "name": "production",
                ...
            }
        }
    }
    ```
    """

    templated: Sequence[str] = tuple({"env", "filename"} | set(Step.templated))

    def __init__(
        self,
        env: str = "dev",
        filename: str = "settings.json",
        key: str = None,
        title: str = None,
    ):
        super().__init__(filename=filename, key=key, title=title)
        self.env = env

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        if self.env not in r[self.key]:
            raise StepExcecutionError(f"environment {self.env} not found in settings")
        if self.key:
            r[self.key] = r[self.key][self.env]
        else:
            r = r[self.key][self.env]
        return r


class Base64DecodeStep(Step):
    """
    Decodes a Base64 string.
    We decode the Base64 string into bytes of unencoded data.
    We then convert the bytes-like object into a string using the provided encoding.
    The decoded value is stored in {params}.{key}.
    """

    templated: Sequence[str] = tuple({"value", "key"} | set(Step.templated))

    def __init__(self, value: str, key: str = "b64decoded", encoding="utf-8", title: str = None):
        super().__init__(title=title)
        self.value = value
        self.key = key
        self.encoding = encoding

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        r[self.key] = b64decode(self.value).decode(self.encoding)
        return r
