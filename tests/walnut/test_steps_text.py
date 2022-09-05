import pytest

from walnut.errors import StepExcecutionError
from walnut.messages import MappingMessage, SequenceMessage, ValueMessage
from walnut.recipe import Recipe
from walnut.steps.text import (
    TextCountStep,
    TextJoinStep,
    TextReplaceStep,
    TextSplitStep,
    TextSubsetStep,
    TextToLowerStep,
    TextToUpperStep,
)

use_cases = {
    "text_to_lower": {
        "cls": TextToLowerStep,
        "input": ValueMessage("Hello World!"),
        "expected": "hello world!",
        "error": None,
    },
    "text_sequence_to_lower": {
        "cls": TextToLowerStep,
        "input": SequenceMessage(["Hello", "World!"]),
        "expected": ["hello", "world!"],
        "error": None,
    },
    "text_to_lower_error": {
        "cls": TextToLowerStep,
        "input": MappingMessage({}),
        "expected": None,
        "error": "TextToLowerStep is expecting a string or sequence of strings",
    },
    "text_to_upper": {
        "cls": TextToUpperStep,
        "input": ValueMessage("Hello World!"),
        "expected": "HELLO WORLD!",
        "error": None,
    },
    "text_sequence_to_upper": {
        "cls": TextToUpperStep,
        "input": SequenceMessage(["Hello", "World!"]),
        "expected": ["HELLO", "WORLD!"],
        "error": None,
    },
    "text_to_upper_error": {
        "cls": TextToUpperStep,
        "input": MappingMessage({}),
        "expected": None,
        "error": "TextToUpperStep is expecting a string or sequence of strings",
    },
}

use_cases_patterns = {
    "text_split_string": {
        "cls": TextSplitStep,
        "input": ValueMessage("hello my beautiful world"),
        "pattern": (True, " "),
        "expected": ["hello", "my", "beautiful", "world"],
        "error": None,
    },
    "text_split_sequence": {
        "cls": TextSplitStep,
        "input": SequenceMessage(["hello my beautiful", "my beautiful world"]),
        "pattern": (True, " "),
        "expected": [["hello", "my", "beautiful"], ["my", "beautiful", "world"]],
        "error": None,
    },
    "text_split_regex_string": {
        "cls": TextSplitStep,
        "input": ValueMessage("hello-my--beautiful-world"),
        "pattern": (False, "-{2}"),
        "expected": ["hello-my", "beautiful-world"],
        "error": None,
    },
    "text_split_regex_sequence": {
        "cls": TextSplitStep,
        "input": SequenceMessage(["hello-my--beautiful", "my-beautiful--world"]),
        "pattern": (False, "-{2}"),
        "expected": [["hello-my", "beautiful"], ["my-beautiful", "world"]],
        "error": None,
    },
    "text_subset_sequence": {
        "cls": TextSubsetStep,
        "input": SequenceMessage(
            [
                "",
                "except Exception as ex:",
                'raise RecipeExcecutionError(f"unexpected error executing the step {step.__class__.__name__}({step.title}): {ex}")'
                "walnut.errors.RecipeExcecutionError: unexpected error executing the step FilterStep(FilterStep): maximum recursion depth exceeded",
                "",
            ]
        ),
        "pattern": (False, ".*Exception.*"),
        "expected": ["except Exception as ex:"],
        "error": None,
    },
    "text_subset_string": {
        "cls": TextSubsetStep,
        "input": ValueMessage("except Exception as ex:"),
        "pattern": (False, ".*Exception.*"),
        "expected": "except Exception as ex:",
        "error": None,
    },
    "text_join_sequence_to_string": {
        "cls": TextJoinStep,
        "input": SequenceMessage(["hello", "my", "world"]),
        "pattern": (True, "-"),
        "expected": "hello-my-world",
        "error": None,
    },
    "text_count_string": {
        "cls": TextCountStep,
        "input": ValueMessage("abc abc xyz abc ahc"),
        "pattern": (False, "a.c"),
        "expected": 4,
        "error": None,
    },
    "text_count_sequence": {
        "cls": TextCountStep,
        "input": SequenceMessage(["abc abc xyz abc ahc", "abc", "a c", "abbc"]),
        "pattern": (False, "a.c"),
        "expected": [4, 1, 1, 0],
        "error": None,
    },
    "text_count_string_fixed": {
        "cls": TextCountStep,
        "input": ValueMessage("abc abc xyz abc ahc"),
        "pattern": (True, "abc"),
        "expected": 0,
        "error": None,
    },
    "text_count_sequence_fixed": {
        "cls": TextCountStep,
        "input": SequenceMessage(["abc abc xyz abc ahc", "abc", "a c", "abbc"]),
        "pattern": (True, "abc"),
        "expected": [0, 1, 0, 0],
        "error": None,
    },
}


def test_step_case_conversions():
    for name, uc in use_cases.items():
        print(f"Executing use case: {name}")
        step = uc["cls"]()
        step.context(Recipe(title="", steps=[]))
        if uc["error"] is None:
            assert step.execute(uc["input"]).get_value() == uc["expected"]
        else:
            with pytest.raises(StepExcecutionError) as err:
                step.execute(uc["input"])
            assert uc["error"] in str(err)


def test_step_pattern_conversions():
    for name, uc in use_cases_patterns.items():
        print(f"Executing use case: {name}")
        step = uc["cls"](pattern=uc["pattern"][1], fixed=uc["pattern"][0])
        step.context(Recipe(title="", steps=[]))
        if uc["error"] is None:
            assert step.execute(uc["input"]).get_value() == uc["expected"]
        else:
            with pytest.raises(StepExcecutionError) as err:
                step.execute(uc["input"])
            assert uc["error"] in str(err)


def test_text_replace_step():
    step = TextReplaceStep("abc", "xyz", fixed=True)
    assert step.execute(ValueMessage("abc")).get_value() == "xyz"

    step = TextReplaceStep("a.c", "xyz", fixed=False)
    assert step.execute(ValueMessage("abc axc 123")).get_value() == "xyz xyz 123"

    step = TextReplaceStep("abc", "xyz", fixed=True)
    assert step.execute(SequenceMessage(["abc", "123", "abc"])).get_value() == [
        "xyz",
        "123",
        "xyz",
    ]

    step = TextReplaceStep("a.c", "xyz", fixed=False)
    assert step.execute(SequenceMessage(["abc axc 123", "123", "abc"])).get_value() == [
        "xyz xyz 123",
        "123",
        "xyz",
    ]
