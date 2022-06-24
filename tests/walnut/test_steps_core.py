import typing as t
import pytest
import walnut
from walnut.errors import StepExcecutionError


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
    assert r["message"] == "Hello world!"


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
    assert r["message"] == {"one": "two"}


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
    assert r["message"] == ["one", "two"]


def test_read_text_file_step():
    r = walnut.Recipe(
        title="ReadFileStep testing suite (text/yaml)",
        steps=[
            walnut.ReadFileStep(
                title="Test Read File Step",
                filename="tests/walnut/data/sample.yaml",
                key="contents",
                data={
                    "kind": "Secret"
                }
            )
        ]
    ).bake()
    assert r is not None
    assert "contents" in r
    assert r["contents"] == "Kind: Secret\n"


def test_read_json_file_step():
    r = walnut.Recipe(
        title="ReadFileStep testing suite (json)",
        steps=[
            walnut.ReadFileStep(
                title="Test Read File Step",
                filename="tests/walnut/data/sample.json",
                key="contents",
                data={
                    "kind": "Secret"
                }
            )
        ]
    ).bake({
        "env": "utest"
    })
    assert r is not None
    assert "contents" in r
    assert "kind" in r["contents"]
    assert r["contents"]["kind"] == "Secret"


def test_load_settings_step():
    r = walnut.Recipe(
        title="LoadSettingsStep testing suite (json)",
        steps=[
            walnut.LoadParamsFromFileStep(
                title="Test Load Settings Step",
                filename="tests/walnut/data/settings.json",
                env="prod", key="settings"
            )
        ]
    ).bake()

    assert r is not None
    assert "settings" in r
    assert "name" in r["settings"]
    assert r["settings"]["name"] == "production"


def test_load_settings_step_with_wrong_key():
    with pytest.raises(StepExcecutionError) as ex:
        walnut.Recipe(
            title="LoadSettingsStep testing suite (json)",
            steps=[
                walnut.LoadParamsFromFileStep(
                    title="Test Load Settings Step",
                    env="dev",
                    filename="tests/walnut/data/settings.json",
                )
            ]
        ).bake()
    assert str(ex.value) == "environment dev not found in settings"


def test_base64decode_step():

    def post_some_base64_string(inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]):
        return {"var": "d2FsbnV0IHJvY2tz"}

    r = walnut.Recipe(
        title="Testing base64 decode step",
        steps=[
            walnut.LambdaStep(fn=post_some_base64_string),
            walnut.Base64DecodeStep(value="{{ inputs.var }}", key="var")
        ]
    ).bake()
    assert r is not None
    assert r["var"] == "walnut rocks"
