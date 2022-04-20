import walnut


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
