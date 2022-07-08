import walnut


def test_recipe_execution():
    """
    Test the basic execution of the Recipe
    """
    # Define and bake the Recipe:
    response = walnut.Recipe(
        title="Testing Recipe",
        steps=[
            # Just Execute a Dummy Step
            walnut.DummyStep("Dummy Step (key={{ store.params.key }})"),
        ]
    ).bake({
        "key": "value"
    })
    # Validate the output:
    assert response is not None
    assert response == "Dummy Step (key=value)"
