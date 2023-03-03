import copy
import subprocess
import typing as t
from base64 import b64decode, b64encode
from json import loads
from time import sleep
from typing import Callable, Sequence

import requests

from walnut.errors import ShortCircuitError, StepExcecutionError, StepRequirementError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.resources import ResourceFactory
from walnut.steps.core import Step, StorageStep
from walnut.steps.validators import validate_input_type


class DummyStep(Step):
    """
    DummyStep is a dummy implementation of a Step that only prints a message on the output
    """

    templated: Sequence[str] = tuple({"message"} | set(Step.templated))

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def process(self, inputs: Message) -> Message:
        sleep(1)
        return ValueMessage(self.message)


class SaveToStorageStep(Step, StorageStep):
    """
    SaveToStorageStep saves the Step input into the Recipe Storage.
    This steps is a passthrough: the input will be available for the next steps. E.g:

    > w.SaveToStorageStep("params.api.password")
    > # Will store the input value of the last executed step in `storage.params.api.password`

    Note: you can not use "dots" into the storage key names. We have 2 use cases:
    - flatten asignation with key = "key"
      > storage["key"] = value
    - nested asignation with key = "nested.key.name"
      > storage["nested"]["key"]["name"] = value
    """

    def __init__(self, key: str, **kwargs):
        super().__init__(**kwargs)
        self.key = key

    def process(self, inputs: Message) -> Message:
        storage = self.get_storage()
        storage[self.key] = inputs.get_value()
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

    def __init__(self, fn: Callable[[t.Any, t.Dict[t.Any, t.Any]], t.Any], **kwargs):
        super().__init__(**kwargs)
        self.fn = fn

    def process(self, inputs: Message) -> Message:
        try:
            return self.fn(inputs.get_value(), self.get_storage().as_dict())
        except Exception as ex:
            raise StepExcecutionError(f"error during lambda function call: {ex}")


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

    def process(self, inputs: Message) -> Message:
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

    @validate_input_type(types=[ValueMessage])
    def process(self, inputs: Message) -> Message:
        v = inputs.get_value()
        if not isinstance(v, str):
            raise StepExcecutionError("Base64DecodeStep requires a string input to encode")
        d = b64decode(str(v)).decode(self.encoding)
        return ValueMessage(d)


class Base64EncodeStep(Step):
    """
    Enecodes a Base64 string.
    We encode the Base64 string into bytes of encoded data.
    We then convert the bytes-like object into a string using the provided encoding.
    """

    def __init__(self, encoding="utf-8", **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding

    @validate_input_type(types=[ValueMessage])
    def process(self, inputs: Message) -> Message:
        v = inputs.get_value()
        if not isinstance(v, str):
            raise StepExcecutionError("Base64EncodeStep requires an string input")
        d = b64encode(v.encode(self.encoding)).decode(self.encoding)
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

    templated: t.Sequence[str] = tuple(
        {"url", "method", "user", "password", "headers"} | set(Step.templated)
    )
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

    def process(self, inputs: Message) -> Message:
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
        self,
        command: t.Sequence[str],
        timeout: int = 60,
        encoding: str = "utf-8",
        shell: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.command = command
        self.timeout = timeout
        self.encoding = encoding
        self.shell = shell

    def process(self, inputs: Message) -> Message:
        r = subprocess.run(
            self.command, capture_output=True, timeout=self.timeout, shell=self.shell
        )
        return MappingMessage(
            {
                "status": r.returncode,
                "stdout": [line.decode(self.encoding) for line in r.stdout.splitlines()],
                "stderr": [line.decode(self.encoding) for line in r.stderr.splitlines()],
            }
        )


class FailStep(Step):
    """
    FailStep is a Step that just fail the execution of the Recipe.
    Why? It's quite useful to early-stop the execution when you are developing a Recipe.

    If the returned result from the function is True, the Recipe will Fail.
    If the funtion result is False or a falsy value, downstream tasks proceed as normal.

    Callable signature:
        fn(Message, t.Dict[t.Any, t.Any]) -> Message
        where:
        - Message is the input data
        - Dict is the Recipe store
    """

    def __init__(
        self, fn: t.Optional[Callable[[t.Any, t.Dict[t.Any, t.Any]], bool]] = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.fn = fn if fn else lambda i, s: True

    def process(self, inputs: Message) -> Message:
        if self.fn and self.fn(inputs, self.get_storage().as_dict()):
            raise StepExcecutionError("FailStep is failing this execution")
        return inputs


class ShortCircuitStep(Step):
    """
    Allows a Recipe to continue based on the result of a python callable

    If the returned result is True, the Recipe will be short-circuited.
    Downstream Steps will be marked with a state of “skipped”.
    If the returned result is False or a truthy value, downstream tasks proceed as normal.

    Callable signature:
        fn(Message, t.Dict[t.Any, t.Any]) -> Message
        where:
        - Message is the input data
        - Dict is the Recipe store
    """

    def __init__(self, fn: Callable[[t.Any, t.Dict[t.Any, t.Any]], bool], **kwargs) -> None:
        super().__init__(**kwargs)
        self.fn = fn

    def process(self, inputs: Message) -> Message:
        if self.fn and self.fn(inputs, self.get_storage().as_dict()):
            raise ShortCircuitError()
        if inputs.get_value() is True:
            raise ShortCircuitError()
        return inputs


class DeclareResourceStep(Step):
    """
    Create resource defines a external resource that you are going to use several times in your recipe.
    Good examples are Database or API connections. Some Steps require a resource to query. E.g: DatabaseQueryStep.
    You can define all the resources you need by name.

    The `name` of the resouce is the string that you should use in the consumer steps to
    refer to this specific resouce.
    On the other hand, `resource` should be a dictionary following the structure:
    {
        "engine": "postgresql|mysql|etc",
        # Engine custom parameters:
        "user": "my-user",
        "password": "my-password",
        "database": "my-database",
        "hot": "localhost"
    }
    Please refer to the `resources` module to list all the available Resources and clients.
    """

    templated: t.Sequence[str] = tuple({"name", "resource"} | set(Step.templated))

    def __init__(self, name: str, resource: t.Union[t.Dict, str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.resource = copy.deepcopy(resource if resource else {})

    def process(self, inputs: Message) -> Message:
        if "engine" not in self.resource:
            raise StepExcecutionError(
                f"Engine key was not defined in the resource: {self.resource}"
            )
        # The engine is defined inside the dictionary. Howerver, we don't need it on the init.
        engine = self.resource["engine"]
        del self.resource["engine"]
        # Call the resource facotry to get the actual Engine.
        r = ResourceFactory.create(engine, **self.resource)
        self.get_resources()[self.name] = r
        self.add_trace(f"{r}")
        return MappingMessage(self.resource)


class TraceStep(Step):
    """
    Adds a custom trace to the high-level execution context. This trace/log will be printed after
    the execution to give the user more information about the execution. E.g:
     • Initializing the Database Environment: ok
     └─► PostgreSQLResource db:postgresql:/tmp/my-socket:my-user:5432/my-database
    """

    templated: t.Sequence[str] = tuple({"trace"} | set(Step.templated))

    def __init__(self, trace: str = None, level: str = "info", **kwargs) -> None:
        super().__init__(**kwargs)
        self.trace = trace
        self.level = level

    def process(self, inputs: Message) -> Message:
        t = self.trace if self.trace else inputs.get_value()
        if isinstance(t, list):
            for tl in t:
                self.add_trace(str(tl), self.level)
        else:
            self.add_trace(str(t), self.level)
        return inputs
