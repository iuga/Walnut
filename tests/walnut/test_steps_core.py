import pytest
import responses
from responses import matchers

import walnut
from walnut.errors import StepExcecutionError
from walnut.messages import Message
from walnut.steps.core import FailStep, ShellStep


def test_store_content():
    """
    Store is a critical feature on Walnut, we should cover and document it.
    """
    r = (
        walnut.Recipe(
            title="Testing store",
            steps=[
                walnut.LambdaStep(fn=lambda x, y: "some_store_value"),
                walnut.StoreOutputStep("some_store_key"),
                walnut.LambdaStep(fn=lambda x, y: {"some_input_key": "some_input_value"}),
                walnut.DummyStep(
                    message="Parameters: {{ store.params.some_param_key }} | Store: {{ store.some_store_key }} | Inputs: {{ inputs['some_input_key'] }}"
                ),
            ],
        )
        .prepare(params={"some_param_key": "some_param_value"})
        .bake()
    )
    assert r is not None
    assert r == "Parameters: some_param_value | Store: some_store_value | Inputs: some_input_value"


def test_template_var_not_resolved_should_fail():
    """
    If one of the templated fields can not be resolved, we should fail.
    """
    r = walnut.Recipe(
        title="Testing template redering",
        steps=[
            walnut.DummyStep(message="This variables does not exist {{ not_found }}"),
        ],
    ).bake()
    assert r is None


def test_step_templated_fields_as_string():
    r = (
        walnut.Recipe(
            title="Testing templated fields when return value is a string",
            steps=[walnut.DummyStep(message="Hello {{ store.params.dest }}!")],
        )
        .prepare(params={"dest": "world"})
        .bake()
    )
    assert r is not None
    assert r == "Hello world!"


def test_step_templated_fields_as_json():
    r = (
        walnut.Recipe(
            title="Testing templated fields when return value is a dict",
            steps=[walnut.DummyStep(message="{{ store.params.out | tojson }}")],
        )
        .prepare(params={"out": {"one": "two"}})
        .bake()
    )
    assert r is not None
    assert r == {"one": "two"}


def test_step_templated_fields_as_list():
    r = (
        walnut.Recipe(
            title="Testing templated fields when return value is a list",
            steps=[walnut.DummyStep(message="{{ store.params.out | tojson | keys }}")],
        )
        .prepare(params={"out": {"one": "a", "two": "b"}})
        .bake()
    )
    assert r is not None
    assert r == ["one", "two"]


def test_read_json_file_step():
    r = (
        walnut.Recipe(
            title="ReadFileStep testing suite (json)",
            steps=[
                walnut.ReadFileStep(
                    title="Test Read File Step",
                    filename="tests/walnut/data/sample.json",
                    data={"kind": "Secret"},
                )
            ],
        )
        .prepare({"env": "utest"})
        .bake()
    )
    assert r is not None
    assert "kind" in r
    assert r["kind"] == "Secret"


def test_base64decode_step():
    r = walnut.Recipe(
        title="Testing base64 decode step",
        steps=[walnut.LambdaStep(fn=lambda x, y: "d2FsbnV0IHJvY2tz"), walnut.Base64DecodeStep()],
    ).bake()
    assert r is not None
    assert r == "walnut rocks"


def test_base64encode_step():
    r = walnut.Recipe(
        title="Testing base64 encode step",
        steps=[walnut.LambdaStep(fn=lambda x, y: "walnut rocks"), walnut.Base64EncodeStep()],
    ).bake()
    assert r is not None
    assert r == "d2FsbnV0IHJvY2tz"


@responses.activate
def test_http_request_step():

    use_cases = {
        "get_200_json": {
            "method": "GET",
            "url": "http://walnut.com/api/1/health",
            "status": 200,
            "headers": {"Accept": "application/json"},
            "payload": None,
            "response": {"status": "healthy"},
        },
        "get_500_json": {
            "method": "GET",
            "url": "http://walnut.com/api/1/health",
            "status": 500,
            "headers": {"Accept": "application/json"},
            "payload": None,
            "response": {"status": "unhealthy"},
        },
        "post_200_json": {
            "method": "POST",
            "url": "http://walnut.com/api/1/health",
            "status": 200,
            "headers": {"Accept": "application/json"},
            "payload": {"client": "walnut"},
            "response": {"status": "ok"},
        },
    }

    for name, uc in use_cases.items():
        print(f"testing use case: {name}")

        m = []
        if uc["headers"]:
            m.append(matchers.header_matcher(uc["headers"]))
        if uc["payload"]:
            m.append(matchers.json_params_matcher(uc["payload"]))

        responses.add(
            uc["method"],
            uc["url"],
            json=uc["response"],
            status=uc["status"],
            match=m,
        )

        r = walnut.Recipe(
            title=f"Testing a simple http request: {name}",
            steps=[
                walnut.HttpRequestStep(
                    method=uc["method"],
                    url=uc["url"],
                    payload=uc["payload"],
                    headers=uc["headers"],
                )
            ],
        ).bake()

        # We should always have a response!
        assert r is not None
        # Validate the response structure:
        assert "url" in r
        assert "method" in r
        assert "headers" in r
        assert "response" in r
        assert "status" in r
        # Validate the response content:
        assert r["url"] == uc["url"]
        assert r["method"] == uc["method"]
        assert r["headers"] == uc["headers"]
        assert r["response"] == uc["response"]
        assert r["status"] == uc["status"]


def test_shell_step():
    r = walnut.Recipe(
        title="Testing base64 decode step",
        steps=[ShellStep(["python", "-c", "print('hello'); print('world');"])],
    ).bake()
    assert r is not None
    assert r["status"] == 0
    assert r["stderr"] == []
    assert r["stdout"] == ["hello", "world"]


def test_fail_step():
    s = FailStep()
    with pytest.raises(StepExcecutionError):
        s.execute(Message())


def test_short_circuit_step():
    r = walnut.Recipe(
        title="Testing Short Circuit Operator",
        steps=[walnut.ShortCircuitStep(fn=lambda x, y: True), walnut.FailStep()],
    ).bake()
    assert r is not None

    with pytest.raises(StepExcecutionError):
        walnut.Recipe(
            title="Testing Short Circuit Operator",
            steps=[walnut.ShortCircuitStep(fn=lambda x, y: False), walnut.FailStep()],
        ).bake()
