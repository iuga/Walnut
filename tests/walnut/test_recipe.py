import walnut


def test_recipe_execution():
    """
    Test the basic execution of the Recipe
    """
    # Define a Dummy Function
    def fn_dummy(params: dict) -> dict:
        return {
            "ping": "pong"
        }
    # Define and bake the Recipe:
    response = walnut.Recipe(
        title="Testing Recipe",
        steps=[
            # Just Execute a Dummy Step
            walnut.DummyStep("Dummy Step Test"),
            # Just a Dummy Lambda
            walnut.LambdaStep("Lambda Step Test", fn_dummy),
            # Print some deprecation warning:
            walnut.WarningStep("Warning Step Test", "deprecation warning")
        ]
    ).bake({
        "key": "value"
    })
    # Validate the output:
    assert response is not None
    assert "key" in response
    assert response["key"] == "value"

    assert "ping" in response
    assert response["ping"] == "pong"

    assert "warnings" in response
    assert response["warnings"][0] == "deprecation warning"
