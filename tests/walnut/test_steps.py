import pytest
import walnut
from walnut.errors import StepExcecutionError


def test_read_text_file_step():
    r = walnut.Recipe(
        title="ReadFileStep testing suite (text/yaml)",
        steps=[
            walnut.ReadFileStep(
                "Test Read File Step",
                "tests/walnut/data/sample.yaml",
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
                "Test Read File Step",
                "tests/walnut/data/sample.json",
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
    assert r["contents"]["env"] == "utest"


def test_load_settings_step():
    r = walnut.Recipe(
        title="LoadSettingsStep testing suite (json)",
        steps=[
            walnut.LoadSettingsStep(
                "Test Load Settings Step",
                env="prod",
                filename="tests/walnut/data/settings.json",
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
                walnut.LoadSettingsStep(
                    "Test Load Settings Step",
                    env="dev",
                    filename="tests/walnut/data/settings.json",
                )
            ]
        ).bake()
    assert str(ex.value) == "environment dev not found in settings"
