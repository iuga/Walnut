from typing import Callable
from json import loads
import io
from contextlib import redirect_stdout
import chevron
from walnut.errors import StepExcecutionError


class Step:
    """
    Step is a concrete implementation of a step that should be executed
    """

    def __init__(self, title: str):
        self.title = title

    def execute(self, params: dict) -> dict:
        """
        Excecute the main logic of the step. It should return a dictionary.
        The content of the returned dictionary will update the "context" dictionary and will be shared with
        downstream Steps.
        :raises StepExcecutionError if there was an error
        """
        return {}

    def close(self):
        """
        Close the asociated resources to this step
        :raises StepExcecutionError if there was an error
        """
        pass


class DummyStep(Step):
    """
    DummyStep is a dummy implementation of a Step that only prints a message on the output
    """

    def __init__(self, title: str):
        super().__init__(title)

    def execute(self, params: dict):
        super().execute(params)


class WarningStep(Step):
    """
    WarningStep logs a warning
    """

    def __init__(self, title: str, message: str):
        super().__init__(title)
        self.message = message

    def execute(self, params: dict) -> dict:
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
            f = io.StringIO()
            with redirect_stdout(f):
                r = self.fn(params)
            out = f.getvalue()
            if out is not None and out != "":
                r["stdout"] = out
            return r
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
    def __init__(self, title: str, env: str = "dev", filename: str = "settings.json", key: str = "settings"):
        super().__init__(title, filename=filename, key=key)
        self.env = env

    def execute(self, params: dict) -> dict:
        r = super().execute(params)
        if self.env not in r[self.key]:
            raise StepExcecutionError(f"environment {self.env} not found in settings")
        r[self.key] = r[self.key][self.env]
        return r
