import pytest

import walnut as w
from walnut.messages import MappingMessage, SequenceMessage, ValueMessage
from walnut.steps.asserts import (
    AssertAllInStep,
    AssertChecksStep,
    AssertEmptyStep,
    AssertEqualStep,
    AssertGreaterOrEqualStep,
    AssertLessOrEqualStep,
    AssertLessStep,
    AssertNotEmptyStep,
    RequireAllInStep,
    RequireChecksStep,
    RequireEmptyStep,
    RequireEqualStep,
    RequireGreaterOrEqualStep,
    RequireLessOrEqualStep,
    RequireLessStep,
    RequireNotEmptyStep,
    AssertGreaterStep,
    RequireGreaterStep
)


use_cases = {
    "assert equal steps": {
        "asserts": [AssertEqualStep, RequireEqualStep],
        "tests": [
            {"input": ValueMessage("x"), "expected": "x", "unexpected": "y"},
            {"input": ValueMessage(42), "expected": 42, "unexpected": 1},
            {"input": ValueMessage(3.14), "expected": 3.14, "unexpected": 2.63},
            {
                "input": MappingMessage({"hello": "world"}),
                "expected": {"hello": "world"},
                "unexpected": {"hi", "planet"},
            },
            {
                "input": SequenceMessage(["a", "b", "c", "d"]),
                "expected": ["a", "b", "c", "d"],
                "unexpected": ["x", "y"],
            },
        ],
    },
    "assert all in steps": {
        "asserts": [AssertAllInStep, RequireAllInStep],
        "tests": [
            {
                "input": SequenceMessage(["a", "b", "c", "d"]),
                "expected": ["a", "b", "c", "d"],
                "unexpected": ["a", "b", "c", "d", "f"],
            },
        ],
    },
    "assert empty steps": {
        "asserts": [AssertEmptyStep, RequireEmptyStep],
        "tests": [{"input": SequenceMessage([]), "exected": True, "no_params": True}],
    },
    "assert not empty steps": {
        "asserts": [AssertNotEmptyStep, RequireNotEmptyStep],
        "tests": [{"input": SequenceMessage([]), "unexpected": True, "no_params": True}],
    },
    "check steps": {
        "asserts": [AssertChecksStep, RequireChecksStep],
        "tests": [
            {
                "input": SequenceMessage([{"a": 1, "b": True, "c": "hello"}]),
                "expected": True,
                "no_params": True,
            },
            {
                "input": SequenceMessage([{"a": 0, "b": False, "c": ""}]),
                "unexpected": True,
                "no_params": True,
            },
        ],
    },
    "greater steps": {
        "asserts": [AssertGreaterStep, RequireGreaterStep],
        "tests": [
            {"input": ValueMessage(42), "expected": 41, "unexpected": 43},
        ],
    },
    "less steps": {
        "asserts": [AssertLessStep, RequireLessStep],
        "tests": [
            {"input": ValueMessage(99), "expected": 100, "unexpected": 98},
        ]
    },
    "greater or equal steps": {
        "asserts": [AssertGreaterOrEqualStep, RequireGreaterOrEqualStep],
        "tests": [
            {"input": ValueMessage(42), "expected": 42, "unexpected": 43},
            {"input": ValueMessage(42), "expected": 41},
        ]
    },
    "less or equal steps": {
        "asserts": [AssertLessOrEqualStep, RequireLessOrEqualStep],
        "tests": [
            {"input": ValueMessage(99), "expected": 99, "unexpected": 98},
            {"input": ValueMessage(99), "expected": 100},
        ]
    }
}


def test_all_assertions():
    """
    For each use case and assertion, execute all tests.
    - input is the Step execution inputs
    - expected is the value when the assertion will be successful
    - unexpected is the value when the assertion will be unsuccessful
    - no_params is required for Asserts that do not expect any parameters to compare.
    """
    for name, uc in use_cases.items():
        for assertClass in uc["asserts"]:
            for t in uc["tests"]:
                if "expected" in t:
                    print(f"Testing: {name} on {assertClass} as successful")
                    if "no_params" in t:
                        assertClass().execute(inputs=t["input"], store={})
                    else:
                        assertClass(t["expected"]).execute(inputs=t["input"], store={})
                if "unexpected" in t:
                    print(f"Testing: {name} on {assertClass} as unsuccessful")
                    with pytest.raises((w.StepAssertionError, w.StepRequirementError)):
                        if "no_params" in t:
                            assertClass().execute(inputs=t["input"], store={})
                        else:
                            assertClass(t["unexpected"]).execute(inputs=t["input"], store={})
