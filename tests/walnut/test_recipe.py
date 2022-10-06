import walnut as w


def test_recipe_execution():
    """
    Test the basic execution of the Recipe
    """
    # Define and bake the Recipe:
    response = (
        w.Recipe(
            title="Testing Recipe",
            steps=[
                # Just Execute a Dummy Step
                w.DummyStep("Dummy Step (key={{ storage.params.key }})"),
            ],
        )
        .prepare(params={"key": "value"})
        .bake()
    )
    # Validate the output:
    assert response is not None
    assert response == "Dummy Step (key=value)"
