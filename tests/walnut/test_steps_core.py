import walnut


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
