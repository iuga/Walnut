import pytest
from walnut.errors import StepExcecutionError
from walnut.messages import MappingMessage, SequenceMessage, ValueMessage
from walnut.steps.text import TextSubsetStep, TextToLowerStep, TextToUpperStep


use_cases = {
    "text_to_lower": {
        "cls": TextToLowerStep,
        "input": ValueMessage("Hello World!"),
        "expected": "hello world!",
        "error": None
    },
    "text_sequence_to_lower": {
        "cls": TextToLowerStep,
        "input": SequenceMessage(["Hello", "World!"]),
        "expected": ["hello", "world!"],
        "error": None
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
        "error": None
    },
    "text_sequence_to_upper": {
        "cls": TextToUpperStep,
        "input": SequenceMessage(["Hello", "World!"]),
        "expected": ["HELLO", "WORLD!"],
        "error": None
    },
    "text_to_upper_error": {
        "cls": TextToUpperStep,
        "input": MappingMessage({}),
        "expected": None,
        "error": "TextToUpperStep is expecting a string or sequence of strings",
    },
}


def test_step_case_conversions():
    for name, uc in use_cases.items():
        print(f"Executing use case: {name}")
        step = uc["cls"]()
        if uc["error"] is None:
            assert step.execute(uc["input"], {}).get_value() == uc["expected"]
        else:
            with pytest.raises(StepExcecutionError) as err:
                step.execute(uc["input"], {})
            assert uc["error"] in str(err)


def test_substep_on_regular_expressions_and_log_input_format():
    s = TextSubsetStep(".*Exception.*")
    m = s.execute(SequenceMessage([
        "",
        "except Exception as ex:",
        'raise RecipeExcecutionError(f"unexpected error executing the step {step.__class__.__name__}({step.title}): {ex}")'
        "walnut.errors.RecipeExcecutionError: unexpected error executing the step FilterStep(FilterStep): maximum recursion depth exceeded",
        ""
    ]), {})
    assert m is not None
    v = m.get_value()
    assert isinstance(v, list)
    assert len(v) == 1
    assert v[0] == "except Exception as ex:"


def test_substep_on_regular_expressions_and_single_text_input():
    s = TextSubsetStep(".*Exception.*")
    m = s.execute(ValueMessage(
        "except Exception as ex:",
    ), {})
    assert m is not None
    v = m.get_value()
    assert isinstance(v, list)
    assert len(v) == 1
    assert v[0] == "except Exception as ex:"
