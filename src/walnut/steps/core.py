from re import template
from typing import Callable, Sequence
from json import loads
from base64 import b64decode
import chevron
from walnut.errors import StepExcecutionError


class Step:
    """
    Step is a concrete implementation of a step that should be executed
    """

    templated: Sequence[str] = ["title"]

    def __init__(self, title: str):
        self.title = title

    def execute(self, params: dict) -> dict:
        """
        Excecute the main logic of the step
        :raises StepExcecutionError if there was an error
        """
        self.render_templated(params)
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

            LambdaStep(title="Executing: {{ settings.name }}")

        Will read from {params}.{settings}.{name} during execution. The output will be: "Executing: Some Name".
        The value in the double curly braces {{ }} is our templated code to be evaluated at runtime.

        Walnut leverages Chevron, a templating framework in Python, as its templating engine.
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
            try:
                value = str(chevron.render(template=value, data=params))
                setattr(self, attr_name, value)
            except Exception as err:
                raise StepExcecutionError(f"Error rendering {attr_name}: {err}")


class DummyStep(Step):
    """
    DummyStep is a dummy implementation of a Step that only prints a message on the output
    """

    def __init__(self, title: str):
        super().__init__(title)

    def execute(self, params: dict):
        return super().execute(params)


class WarningStep(Step):
    """
    WarningStep logs a warning
    """

    templated: Sequence[str] = tuple({"message"} | set(Step.templated))

    def __init__(self, title: str, message: str):
        super().__init__(title)
        self.message = message

    def execute(self, params: dict) -> dict:
        super().execute(params)
        w = []
        if "warnings" in params:
            w = params["warnings"]
        w.append(self.message)
        return {"warnings": w}


class LambdaStep(Step):
    """
    LambdaStep executes the provided function
    """

    def __init__(self, title: str, fn: Callable[[dict], dict]):
        super().__init__(title)
        self.fn = fn

    def execute(self, params: dict):
        super().execute(params)
        try:
            return self.fn(params)
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

    def __init__(self, title: str, filename: str, key: str = "raw", data: dict = {}):
        super().__init__(title)
        self.key = key
        self.filename = filename
        self.data = data

    def execute(self, params: dict) -> dict:
        r = super().execute(params)
        if self.filename.endswith(".json"):
            r[self.key] = self.read_json(params)
        else:
            r[self.key] = self.read_raw(params)
        return r

    def read_raw(self, params: dict) -> str:
        self.data["params"] = params
        with open(self.filename, "r") as fp:
            return str(chevron.render(fp, self.data))

    def read_json(self, params: dict) -> dict:
        return loads(self.read_raw(params))


class LoadSettingsStep(ReadFileStep):
    """
    LoadSettingsStep loads to the Pipeline the settings defined in `settings.json`.
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
        "settings": {
            "name": "production",
            ...
        }
    }
    ```
    """

    def __init__(
        self,
        title: str,
        env: str = "dev",
        filename: str = "settings.json",
        key: str = "settings",
    ):
        super().__init__(title, filename=filename, key=key)
        self.env = env

    def execute(self, params: dict) -> dict:
        r = super().execute(params)
        if self.env not in r[self.key]:
            raise StepExcecutionError(f"environment {self.env} not found in settings")
        r[self.key] = r[self.key][self.env]
        return r


class Base64DecodeStep(Step):
    """
    Decodes a Base64 string.
    We decode the Base64 string into bytes of unencoded data.
    We then convert the bytes-like object into a string using the provided encoding.
    The decoded value is stored in {params}.{key}.
    """

    templated: Sequence[str] = tuple({"value", "key"} | set(Step.templated))

    def __init__(
        self, title: str, value: str, key: str = "b64decoded", encoding="utf-8"
    ):
        super().__init__(title)
        self.value = value
        self.key = key
        self.encoding = encoding

    def execute(self, params: dict) -> dict:
        r = super().execute(params)
        r[self.key] = b64decode(self.value).decode(self.encoding)
        return r
