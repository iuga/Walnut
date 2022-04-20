from typing import Callable
from json import loads
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
        Excecute the main logic of the step
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
