import pytest

import walnut as w


use_cases = {
    "string": {"output": "x"},
    "int": {"output": 42},
    "float": {"output": 3.14},
    "dict": {"output": {"hello": "world"}},
    "list": {"output": ["a", "b", "c", "d"]},
    "check_success": [{"a": 1, "b": True, "c": "hello"}],
    "check_failure": [{"a": 0, "b": False, "c": ""}],
    "empty": [],
    "not_empty": ["a", "b"]
}


def test_assert_and_require():
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v="no").execute(inputs=use_cases["string"], store={})
    with pytest.raises(w.StepRequirementError):
        w.RequireEqualStep(v="no").execute(inputs=use_cases["string"], store={})


def test_assert_equal_step():
    w.AssertEqualStep(v="x").execute(inputs=use_cases["string"], store={})
    w.AssertEqualStep(v=42).execute(inputs=use_cases["int"], store={})
    w.AssertEqualStep(v=3.14).execute(inputs=use_cases["float"], store={})
    w.AssertEqualStep(v={"hello": "world"}).execute(inputs=use_cases["dict"], store={})
    w.AssertEqualStep(v=["a", "b", "c", "d"]).execute(inputs=use_cases["list"], store={})


def test_assert_equal_failures_step():
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v="z").execute(inputs=use_cases["string"], store={})
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v=3).execute(inputs=use_cases["int"], store={})
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v="no").execute(inputs=use_cases["float"], store={})
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v={"good": "morning"}).execute(inputs=use_cases["dict"], store={})
    with pytest.raises(w.StepAssertionError):
        w.AssertEqualStep(v=["a", "b"]).execute(inputs=use_cases["list"], store={})


def test_assert_all_in_step():
    w.AssertAllInStep(needles=["d", "c", "b", "a"]).execute(inputs=use_cases["list"], store={})


def test_assert_all_in_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertAllInStep(needles=["a", "b", "c", "d", "f"]).execute(inputs=use_cases["list"], store={})


def test_check_step():
    w.AssertChecksStep().execute(inputs=use_cases["check_success"], store={})


def test_check_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertChecksStep().execute(inputs=use_cases["check_failure"], store={})


def test_empty_step():
    w.AssertEmptyStep().execute(inputs=use_cases["empty"], store={})


def test_empty_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertEmptyStep().execute(inputs=use_cases["not_empty"], store={})


def test_not_empty_step():
    w.AssertNotEmptyStep().execute(inputs=use_cases["not_empty"], store={})


def test_not_empty_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertNotEmptyStep().execute(inputs=use_cases["empty"], store={})


def test_greater_step():
    w.AssertGreaterStep(40).execute(inputs=use_cases["int"], store={})


def test_greater_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertGreaterStep(100).execute(inputs=use_cases["int"], store={})


def test_greater_equal_step():
    w.AssertGreaterOrEqualStep(42).execute(inputs=use_cases["int"], store={})


def test_greater_equal_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertGreaterOrEqualStep(100).execute(inputs=use_cases["int"], store={})


def test_less_step():
    w.AssertLessStep(100).execute(inputs=use_cases["int"], store={})


def test_less_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertLessStep(40).execute(inputs=use_cases["int"], store={})


def test_less_equal_step():
    w.AssertLessStep(100).execute(inputs=use_cases["int"], store={})


def test_less_equal_step_failure():
    with pytest.raises(w.StepAssertionError):
        w.AssertLessStep(42).execute(inputs=use_cases["int"], store={})
