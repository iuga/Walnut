import walnut
import responses
from responses import matchers


def test_step_templated_fields_as_string():
    r = walnut.Recipe(
        title="Testing templated fields when return value is a string",
        steps=[
            walnut.DummyStep(message="Hello {{ store.params.dest }}!")
        ]
    ).bake(
        params={
            "dest": "world"
        }
    )
    assert r is not None
    assert r == "Hello world!"


def test_step_templated_fields_as_json():
    r = walnut.Recipe(
        title="Testing templated fields when return value is a dict",
        steps=[
            walnut.DummyStep(message="{{ store.params.out | tojson }}")
        ]
    ).bake(
        params={
            "out": {
                "one": "two"
            }
        }
    )
    assert r is not None
    assert r == {"one": "two"}


def test_step_templated_fields_as_list():
    r = walnut.Recipe(
        title="Testing templated fields when return value is a list",
        steps=[
            walnut.DummyStep(message="{{ store.params.out | tojson | keys }}")
        ]
    ).bake(
        params={
            "out": {
                "one": "a",
                "two": "b"
            }
        }
    )
    assert r is not None
    assert r == ["one", "two"]


def test_read_json_file_step():
    r = walnut.Recipe(
        title="ReadFileStep testing suite (json)",
        steps=[
            walnut.ReadFileStep(
                title="Test Read File Step",
                filename="tests/walnut/data/sample.json",
                data={
                    "kind": "Secret"
                }
            )
        ]
    ).bake({
        "env": "utest"
    })
    assert r is not None
    assert "kind" in r
    assert r["kind"] == "Secret"


def test_base64decode_step():
    r = walnut.Recipe(
        title="Testing base64 decode step",
        steps=[
            walnut.LambdaStep(fn=lambda x, y: "d2FsbnV0IHJvY2tz"),
            walnut.Base64DecodeStep()
        ]
    ).bake()
    assert r is not None
    assert r == "walnut rocks"


@responses.activate
def test_http_request_step():

    use_cases = {
        "get_200_json": {
            "method": "GET",
            "url": "http://walnut.com/api/1/health",
            "status": 200,
            "headers": {"Accept": "application/json"},
            "body": None,
            "response": {"status": "healthy"}
        },
        "get_500_json": {
            "method": "GET",
            "url": "http://walnut.com/api/1/health",
            "status": 500,
            "headers": {"Accept": "application/json"},
            "body": None,
            "response": {"status": "unhealthy"}
        },
        "post_200_json": {
            "method": "POST",
            "url": "http://walnut.com/api/1/health",
            "status": 200,
            "headers": {"Accept": "application/json"},
            "body": {"client": "walnut"},
            "response": {"status": "ok"}
        }
    }

    for name, uc in use_cases.items():
        print(f"testing use case: {name}")

        m = []
        if uc["headers"]:
            m.append(matchers.header_matcher(uc["headers"]))
        if uc["body"]:
            m.append(matchers.json_params_matcher(uc["body"]))

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
                walnut.HttpRequestStep(method=uc["method"], url=uc["url"], json=uc["body"], headers=uc["headers"])
            ]
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
