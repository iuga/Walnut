import walnut as w


def test_store_content():
    """
    Storage is a critical feature on Walnut, we should cover and document it.
    """
    r = (
        w.Recipe(
            title="Testing Storage",
            steps=[
                w.LambdaStep(fn=lambda x, y: "some_value_to_store"),
                w.SaveToStorageStep("some_storage_key"),
                w.LambdaStep(fn=lambda x, y: {"some_input_key": "some_input_value"}),
                w.DummyStep(
                    message="Parameters: {{ storage.params.some_param_key }} | Store: {{ storage.some_storage_key }} | Inputs: {{ inputs['some_input_key'] }}"
                ),
            ],
        )
        .prepare(params={"some_param_key": "some_param_value"})
        .bake()
    )
    assert r is not None
    assert (
        r == "Parameters: some_param_value | Store: some_value_to_store | Inputs: some_input_value"
    )


def test_template_var_not_resolved_should_fail():
    """
    If one of the templated fields can not be resolved, we should fail.
    """
    r = w.Recipe(
        title="Testing template redering",
        steps=[
            w.DummyStep(message="This variables does not exist {{ not_found }}"),
        ],
    ).bake()
    assert r is None


def test_step_templated_fields_as_string():
    r = (
        w.Recipe(
            title="Testing templated fields when return value is a string",
            steps=[w.DummyStep(message="Hello {{ storage.params.dest }}!")],
        )
        .prepare(params={"dest": "world"})
        .bake()
    )
    assert r is not None
    assert r == "Hello world!"


def test_step_templated_fields_as_json():
    r = (
        w.Recipe(
            title="Testing templated fields when return value is a dict",
            steps=[w.DummyStep(message="{{ storage.params.out | tojson }}")],
        )
        .prepare(params={"out": {"one": "two"}})
        .bake()
    )
    assert r is not None
    assert r == {"one": "two"}


def test_step_templated_fields_as_list():
    r = (
        w.Recipe(
            title="Testing templated fields when return value is a list",
            steps=[w.DummyStep(message="{{ storage.params.out | tojson | keys }}")],
        )
        .prepare(params={"out": {"one": "a", "two": "b"}})
        .bake()
    )
    assert r is not None
    assert r == ["one", "two"]


def test_step_templated_list_and_nested_fields():
    r = (
        w.Recipe(
            title="Testing templated fields that are dictionaries",
            steps=[
                w.DummyStep(
                    message=[
                        "hello",
                        "{{ storage.params.dest }}",
                        "world",
                        ["nested", "{{ storage.params.dest }}"],
                    ]
                )
            ],
        )
        .prepare(params={"dest": "crazy"})
        .bake()
    )
    assert r is not None
    assert r == ["hello", "crazy", "world", ["nested", "crazy"]]


def test_step_templated_dict_and_nested_fields():
    r = (
        w.Recipe(
            title="Testing templated fields that are dictionaries",
            steps=[
                w.DummyStep(
                    message={
                        "hello": "world",
                        "msg": "{{ storage.params.dest }}",
                        "thank": "you",
                        "nested": {
                            "hello": "{{ storage.params.dest }}",
                            "list": [">", "{{ storage.params.dest }}"],
                        },
                    }
                )
            ],
        )
        .prepare(params={"dest": "world"})
        .bake()
    )
    assert r is not None
    assert r == {
        "hello": "world",
        "msg": "world",
        "thank": "you",
        "nested": {"hello": "world", "list": [">", "world"]},
    }
