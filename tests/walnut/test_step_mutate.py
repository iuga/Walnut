import pytest
import walnut
from walnut.errors import StepExcecutionError


#
# SelectStep Tests...
#


def test_select_step_with_nested_dicts_and_list_as_result():
    r = walnut.Recipe(
        title="Testing mutate steps: SelectStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "a": {
                    "b": {
                        "c": {
                            "d": ["hello", "world"]
                        }
                    }
                }
            }),
            walnut.SelectStep(expression="a.b.c.d")
        ]
    ).bake()
    assert r is not None
    assert r["out"] == ["hello", "world"]


def test_select_step_with_nested_dicts_and_dict_as_result():
    r = walnut.Recipe(
        title="Testing mutate steps: SelectStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "a": {
                    "b": {"hello": "world"}
                }
            }),
            walnut.SelectStep(expression="a.b")
        ]
    ).bake()
    assert r is not None
    assert r["out"] == {"hello": "world"}


def test_select_step_without_input_data_should_fail():
    with pytest.raises(StepExcecutionError) as ex:
        walnut.Recipe(
            title="Testing mutate steps: SelectStep",
            steps=[
                walnut.SelectStep(expression="a.b")
            ]
        ).bake()
    assert str(ex.value) == "SelectStep does not have any input data to mutate"


#
# FilterStep Tests...
#


def test_filter_on_simple_list_should_work_of_course():
    r = walnut.Recipe(
        title="Testing mutate steps: FilterStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "x": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            }),
            walnut.FilterStep(fn=lambda x: x >= 5)
        ]
    ).bake()
    assert r is not None
    assert "out" in r
    assert len(r["out"]) == 5
    assert r["out"] == [5, 6, 7, 8, 9]


def test_filter_on_dictionaries_at_top_level_should_be_considered():
    r = walnut.Recipe(
        title="Testing mutate steps: FilterStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "a": [
                    {"id": "a", "include": "yes"},
                    {"id": "b", "include": "no"},
                    {"id": "c", "include": "yes"},
                ],
                "b": [
                    {"id": "d", "include": "no"},
                    {"id": "e", "include": "yes"},
                    {"id": "f", "include": "no"},
                ],
                "c": [
                    {"id": "g", "include": "no", "d": [
                        {"id": "h", "include": "yes"}
                    ]},
                ]
            }),
            walnut.FilterStep(fn=lambda x: x["include"] == "yes")
        ]
    ).bake()
    assert r is not None
    assert "out" in r
    assert len(r["out"]) == 3
    assert r["out"][0]["id"] == "a"
    assert r["out"][1]["id"] == "c"
    assert r["out"][2]["id"] == "e"
    # Note: id=h is nested and should not be included.


#
# MapStep
#


def test_mapstep_on_a_simple_list():
    r = walnut.Recipe(
        title="Testing mutate steps: MapStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "x": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            }),
            walnut.MapStep(fn=lambda x: x * 2)
        ]
    ).bake()
    assert r is not None
    assert "out" in r
    assert len(r["out"]) == 9
    assert r["out"] == [2, 4, 6, 8, 10, 12, 14, 16, 18]


#
# ReduceStep
#


def test_map_step():
    r = walnut.Recipe(
        title="Testing mutate steps: ReduceStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: {
                "x": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            }),
            walnut.ReduceStep(fn=lambda x, y: x + y)
        ]
    ).bake()
    assert r is not None
    assert "out" in r
    assert r["out"] == 45
