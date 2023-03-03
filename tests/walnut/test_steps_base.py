import pytest
import responses
from responses import matchers

import walnut as w
from walnut.errors import StepExcecutionError
from walnut.messages import Message
from walnut.steps.base import FailStep, ShellStep


def test_read_json_file_step():
    r = (
        w.Recipe(
            title="ReadFileStep testing suite (json)",
            steps=[
                w.ReadFileStep(
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
    r = w.Recipe(
        title="Testing base64 decode step",
        steps=[w.LambdaStep(fn=lambda x, y: "d2FsbnV0IHJvY2tz"), w.Base64DecodeStep()],
    ).bake()
    assert r is not None
    assert r == "walnut rocks"


def test_base64encode_step():
    r = w.Recipe(
        title="Testing base64 encode step",
        steps=[w.LambdaStep(fn=lambda x, y: "walnut rocks"), w.Base64EncodeStep()],
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

        r = w.Recipe(
            title=f"Testing a simple http request: {name}",
            steps=[
                w.HttpRequestStep(
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
    r = w.Recipe(
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
    r = w.Recipe(
        title="Testing Short Circuit Operator",
        steps=[w.ShortCircuitStep(fn=lambda x, y: True), w.FailStep()],
    ).bake()
    assert r is not None

    with pytest.raises(StepExcecutionError):
        w.Recipe(
            title="Testing Short Circuit Operator",
            steps=[w.ShortCircuitStep(fn=lambda x, y: False), w.FailStep()],
        ).bake()
