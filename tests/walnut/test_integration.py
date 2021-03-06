import walnut as w


def test_load_settings_and_execute_recipe():
    r = w.Recipe(
        title="LoadSettingsStep testing suite (json)",
        steps=[
            w.DummyStep("Environment is {{ store.params.name }}")
        ]
    ).bake(
        w.ReadFileStep(
            filename="tests/walnut/data/settings.json",
            callbacks=[w.SelectStep("prod")]
        )
    )

    assert r is not None
    assert r == "Environment is production"
