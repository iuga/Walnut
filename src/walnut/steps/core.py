from __future__ import annotations

import subprocess
import typing as t
from abc import ABC
from base64 import b64decode
from functools import reduce
from json import dumps, loads
from operator import getitem
from typing import Callable, Sequence

import requests
from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

from walnut.errors import ShortCircuitError, StepExcecutionError, StepRequirementError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage


class Step:
    """
    Step is a concrete implementation of a step that should be executed.
    """

    templated: Sequence[str] = []

    def __init__(self, *, title: str = None, callbacks: list[Step] = None, **kwargs) -> None:
        self.title = title if title else str(self.__class__.__name__)
        self.callbacks = callbacks if callbacks else []
        self.ctx = {}
        self.jinja_env = Environment(undefined=StrictUndefined)

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
        self.render_templated({"inputs": inputs.get_value(), "store": store})
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

        While also the following filters "{{ settings.name | json }}":
        - `x | json` to get the result as a dictionary
        """
        # For each one of the step attributes that should be templated:
        for attr_name in self.templated:
            try:
                # Get the valus inside the variable ( the jinja template )
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
            # Render the value using Jinja
            value = self.render_string(value, params)
            try:
                # TODO: Convert to JSON if possible. We should parse the value and search for | json instead of this:
                value = loads(value)
            except Exception:
                # print(f"[warn] >> not able to json format the value {value}")
                pass  # Nothing to do here...
            setattr(self, attr_name, value)

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

    def context(self, recipe: t.Any = None) -> Step:
        """
        Set the context of this Step, like the Recipe executing it.
        """
        if recipe:
            self.ctx["recipe"] = recipe
        return self

    def get_resource(self, resource_id: str) -> t.Any:
        """
        Returns a resource with the given name or id.
        These resources are added to the Recipe using the resources() method:

            Recipe().resources({
                "id": Resource
            }).bake(...)
        """
        if "recipe" not in self.ctx:
            raise StepExcecutionError("context not set. this should never happen.")
        return self.ctx["recipe"].get_resource(resource_id)

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
    The content of input will be available for all next steps.
    We have 2 use cases:
    - flatten asignation with key = "key"
      > store["key"] = value
    - nested asignation with key = "nested.key.name"
      > store["nested"]["key"]["name"] = value
    Note: you can not use "dots" into the storage key names.
    """

    def __init__(self, key: str, **kwargs):
        super().__init__(**kwargs)
        self.key = key

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        nested = "." in self.key
        if nested:
            self.store = self.update_nested_item(store, self.key.split("."), inputs.get_value())
        else:
            store[self.key] = inputs.get_value()
        return inputs

    def update_nested_item(self, store, path, value):
        """Update item in nested dictionary"""
        reduce(getitem, path[:-1], store)[path[-1]] = value
        return store


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

    def __init__(self, fn: Callable[[t.Any, t.Dict[t.Any, t.Any]], t.Any], **kwargs):
        super().__init__(**kwargs)
        self.fn = fn

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        try:
            return self.fn(inputs.get_value(), store)
        except Exception as ex:
            raise StepExcecutionError(f"error during lambda function call: {ex}")


class FailStep(Step):
    """
    FailStep is a Step that just fail the execution of the Recipe.
    Why? It's quite useful to early-stop the execution when you are developing a Recipe.
    """

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        raise StepExcecutionError("FailStep is failing this execution :police:")


class ReadFileStep(Step):
    """
    ReadFileStep reads the text file (txt, json, yaml, etc) and return the content.
    If template is defined, replace the keys of the dictionary with the values using the moustache format:
    name={{ name }} -> { "name": "Walnut" } -> name=Walnut

    You could load a dictionary from a json file in order to be used as Recipe parameters or Step in the Recipe.
    To subsets a given environment from the json that's why the settings.json file should follow the structure:


    """

    def __init__(self, filename: str, data: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename
        self.data = data if data else {}

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if self.filename.endswith(".json"):
            m = self.read_json(self.data)
        elif self.filename.endswith(".yaml") or self.filename.endswith(".yml"):
            raise NotImplementedError("yaml not supported yet")
        else:
            m = self.read_raw(self.data)
        return m

    def read_raw(self, data: dict) -> Message:
        with open(self.filename, "r") as fp:
            c = fp.read()
            c = self.render_string(c, self.data)
            return ValueMessage(c)

    def read_json(self, data: dict) -> MappingMessage:
        m = self.read_raw(data)
        c = loads(str(m.get_value()))
        return MappingMessage(c)


class Base64DecodeStep(Step):
    """
    Decodes a Base64 string.
    We decode the Base64 string into bytes of unencoded data.
    We then convert the bytes-like object into a string using the provided encoding.
    """

    def __init__(self, encoding="utf-8", **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if not isinstance(inputs, ValueMessage):
            raise StepExcecutionError("Base64DecodeStep requires an input string value to decode")
        d = b64decode(str(inputs.get_value())).decode(self.encoding)
        return ValueMessage(d)


class HttpRequestStep(Step):
    """
    HttpRequestStep is a simple, yet elegant, HTTP Step built over requets.

    :params url - for the request.
    :params method - for the request: GET, OPTIONS, HEAD, POST, PUT, PATCH, or DELETE.
    :params payload – (optional) A JSON serializable Python object to send in the body of the Request.
                      or a Bytes like content. It must match with the parameter `payload_type`
    :params payload_type - (optional) Payload and Response language/format. [bytes, json, html, input]
                           if `input` the Step input value will be use as payload.
    :params headers - (optional) Dictionary of HTTP Headers to send with the Request.
    :params user - (optional) Auth user to enable Basic/Digest/Custom HTTP Auth.
    :params password - (optional) Auth password to enable Basic/Digest/Custom HTTP Auth.

    Response example:
    {
        "url": "http://...",
        "method": "POST",
        "headers": {"accept": "application/json"},
        "status": 200,
        "response": {"message": "some json response"}
    }
    """

    templated: t.Sequence[str] = tuple({"url", "method", "user", "password"} | set(Step.templated))
    PAYLOAD_JSON: str = "json"
    PAYLOAD_BYTES: str = "bytes"
    PAYLOAD_INPUT: str = "input"
    PAYLOAD_HTML: str = "html"
    PAYLOAD_TYPES: t.Sequence[str] = [PAYLOAD_JSON, PAYLOAD_BYTES, PAYLOAD_INPUT, PAYLOAD_HTML]

    def __init__(
        self,
        url: str,
        method: str = "POST",
        payload: t.Any = None,
        payload_type: str = PAYLOAD_JSON,
        headers: t.Dict = None,
        user: t.Text = None,
        password: t.Text = None,
        validate: t.Optional[t.Callable[[t.Any], bool]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.method = method
        self.payload = payload
        self.payload_type = payload_type
        self.headers = headers
        self.user = user
        self.password = password
        self.validate = validate

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        # Validate the payload type
        if self.payload_type not in self.PAYLOAD_TYPES:
            raise StepExcecutionError(
                "payload type {self.payload_type} not supported: {self.PAYLOAD_TYPES}"
            )
        # If there is no data (json or data) use the inputs as default:
        if self.payload_type == self.PAYLOAD_INPUT:
            self.payload = inputs.get_value()

        json_content = (
            self.payload
            if self.payload_type == self.PAYLOAD_JSON
            or isinstance(inputs, (MappingMessage, SequenceMessage))
            else None
        )
        data_content = (
            self.payload
            if self.payload_type in [self.PAYLOAD_BYTES, self.PAYLOAD_HTML]
            or isinstance(inputs, (ValueMessage))
            else None
        )

        self.debug(
            f"[{self.method}] {self.url} ({self.user}@{self.password}) "
            f"with headers {self.headers} "
            f"and payload {json_content if json_content else data_content}"
        )

        r = requests.request(
            method=self.method,
            url=self.url,
            json=json_content,
            data=data_content,
            headers=self.headers,
            auth=None if not self.user and not self.password else (self.user, self.password),
        )

        if self.payload_type in [self.PAYLOAD_JSON, self.PAYLOAD_INPUT]:
            response = r.json()
        else:
            response = r.text

        msg = MappingMessage(
            {
                "url": self.url,
                "method": self.method,
                "headers": self.headers,
                "status": r.status_code,
                "response": response,
            }
        )
        self.debug(str(msg))

        v = self.validate(msg.get_value()) if self.validate else True
        if not v:
            raise StepRequirementError(f"Http response {response} is not valid")

        return msg


class ShellStep(Step):
    """
    ShellStep allows you to spawn new processes, connect to their input/output/error pipes, and obtain their return codes.
    Returns:
        - "status" with the process status code
        - "stdout" with a list of the stdout lines as string
        - "stderr" with a list of the stderr lines as string
    """

    def __init__(
        self, command: t.Sequence[str], timeout: int = 60, encoding: str = "utf-8", **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.command = command
        self.timeout = timeout
        self.encoding = encoding

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        r = subprocess.run(self.command, capture_output=True, timeout=self.timeout)
        return MappingMessage(
            {
                "status": r.returncode,
                "stdout": [line.decode(self.encoding) for line in r.stdout.splitlines()],
                "stderr": [line.decode(self.encoding) for line in r.stderr.splitlines()],
            }
        )


class ShortCircuitStep(Step):
    """
    Allows a Recipe to continue based on the result of a python callable

    If the returned result is True, the Recipe will be short-circuited.
    Downstream Steps will be marked with a state of “skipped”.
    If the returned result is False or a truthy value, downstream tasks proceed as normal
    """

    def __init__(self, fn: Callable[[t.Any, t.Dict[t.Any, t.Any]], bool], **kwargs) -> None:
        super().__init__(**kwargs)
        self.fn = fn

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if self.fn and self.fn(inputs, store):
            raise ShortCircuitError()
        if inputs.get_value() is True:
            raise ShortCircuitError()
        return inputs
