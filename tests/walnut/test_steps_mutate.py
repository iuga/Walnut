import pytest

import walnut
from walnut.errors import StepExcecutionError, StepValidationError
from walnut.messages import MappingMessage, SequenceMessage, ValueMessage

#
# SelectStep Tests...
#


def test_select_step_with_nested_dicts_and_list_as_result():
    r = walnut.Recipe(
        title="Testing mutate steps: SelectStep",
        steps=[
            walnut.LambdaStep(
                fn=lambda i, s: MappingMessage({"a": {"b": {"c": {"d": ["hello", "world"]}}}})
            ),
            walnut.SelectStep("a.b.c.d"),
        ],
    ).bake()
    assert r is not None
    assert r == ["hello", "world"]


def test_select_step_with_nested_dicts_and_dict_as_result():
    r = walnut.Recipe(
        title="Testing mutate steps: SelectStep",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: MappingMessage({"a": {"b": {"hello": "world"}}})),
            walnut.SelectStep("a.b"),
        ],
    ).bake()
    assert r is not None
    assert r == {"hello": "world"}


def test_select_value_message_not_supported_on_select():
    with pytest.raises(StepValidationError) as ex:
        walnut.Recipe(
            title="Testing mutate steps: SelectStep",
            steps=[
                walnut.LambdaStep(fn=lambda i, s: ValueMessage(42)),
                walnut.SelectStep("a"),
            ],
        ).bake()
    assert "ValueMessage not supported" in str(ex.value)


def test_select_value_message_not_supported_on_select_2():
    r = walnut.Recipe(
        title="Testing mutate steps: SelectStep on Sequences",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: SequenceMessage([1, 2, 3, 4])),
            walnut.SelectStep("[0:2]"),
        ],
    ).bake()
    r == [1, 2]


#
# FilterStep Tests...
#


def test_filter_on_simple_list_should_work_of_course():
    r = walnut.Recipe(
        title="Testing mutate steps: FilterStep on SequenceMessage",
        steps=[
            walnut.LambdaStep(fn=lambda i, s: SequenceMessage([1, 2, 3, 4, 5, 6, 7, 8, 9])),
            walnut.FilterStep(fn=lambda x: x >= 5),
        ],
    ).bake()
    assert r is not None
    assert len(r) == 5
    assert r == [5, 6, 7, 8, 9]


#
# MapStep
#


def test_mapstep_on_a_simple_list():
    r = walnut.Recipe(
        title="Testing mutate steps: MapStep",
        steps=[
            walnut.LambdaStep(
                fn=lambda i, s: SequenceMessage(
                    [1, 2, 3, 4, 5, 6, 7, 8, 9],
                )
            ),
            walnut.MapStep(lambda x: x * 2),
        ],
    ).bake()
    assert r is not None
    assert len(r) == 9
    assert r == [2, 4, 6, 8, 10, 12, 14, 16, 18]


#
# ReduceStep
#


def test_map_step():
    r = walnut.Recipe(
        title="Testing mutate steps: ReduceStep",
        steps=[
            walnut.LambdaStep(
                fn=lambda i, s: SequenceMessage(
                    [1, 2, 3, 4, 5, 6, 7, 8, 9],
                )
            ),
            walnut.ReduceStep(fn=lambda x, y: x + y),
        ],
    ).bake()
    assert r is not None
    assert r == 45
