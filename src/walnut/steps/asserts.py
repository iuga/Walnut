import typing as t

from walnut import Step, StepAssertionError, StepRequirementError
from walnut.errors import StepValidationError
from walnut.messages import Message, ValueMessage, SequenceMessage, MappingMessage


class ValidateStep(Step):
    """
    ValidateStep is an abstract class used to declare data validations.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def fail(self, message: str) -> None:
        raise NotImplementedError()


class Assertion():
    """
    AssertStep is an abstract base class that declares a data assertion error.
    We will fail the step but continue the execution.
    """
    def fail(self, message) -> None:
        """
        fail() defines the failure mechanism.
        Assert will report and continue the execution
        """
        raise StepAssertionError(message)


class Requirement():
    """
    RequireStep is an abstract base class that declares a data assertion error.
    We will fail the step and interrupt the execution.
    """
    def fail(self, message) -> None:
        """
        fail defines the failure mechanism.
        Assert will report and continue the execution
        """
        raise StepRequirementError(message)


class ValidateChecksStep(ValidateStep):

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if not isinstance(inputs, SequenceMessage):
            raise StepValidationError("ValidateChecksStep requires a sequence of elements with one item")
        x = inputs.get_value()
        if not x:
            self.fail(f"element to evaluate is empty: {x}")
        if len(x) != 1:
            self.fail("returned multiple or zero elements. failing the assertion")
        # It's an interator, get the first row:
        failed_checks = {}
        for col, val in x[0].items():
            if not bool(val):
                failed_checks[col] = val
        if len(failed_checks) != 0:
            self.fail(f"one or more checks failed. {failed_checks}")
        return inputs


class AssertChecksStep(Assertion, ValidateChecksStep):
    """
    AssertChecksStep performs checks against a single dict observation.
    Note: This step expects a list containing a single dict element.
    Each value on that element is evaluated using python bool casting.
    If any of the values return False the check is failed and errors out.

    Note that Python bool casting evals the following as False:
    - False
    - 0
    - Empty string ("")
    - Empty list ([])
    - Empty dictionary or set ({})

    This Step can be used as a data quality check in your pipeline, and depending on where you put it in
    your Recipe, you have the choice to stop the critical path, preventing from publishing dubious data, or
    on the side and receive email alerts without stopping the progress of the Recipe.

    The Step idea, documentation and logic was inspired from Airfow.
    """
    pass


class RequireChecksStep(Requirement, ValidateChecksStep):
    """
    RequireChecksStep performs checks against a single dict observation.
    Note: This step expects a list containing a single dict element.
    Each value on that element is evaluated using python bool casting.
    If any of the values return False the check is failed and errors out.

    Note that Python bool casting evals the following as False:
    - False
    - 0
    - Empty string ("")
    - Empty list ([])
    - Empty dictionary or set ({})

    This Step can be used as a data quality check in your pipeline, and depending on where you put it in
    your Recipe, you have the choice to stop the critical path, preventing from publishing dubious data, or
    on the side and receive email alerts without stopping the progress of the Recipe.

    The Step idea, documentation and logic was inspired from Airfow.
    """
    pass


class ValidateEmptyStep(ValidateStep):
    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if len(x) != 0:
            self.fail(f"element is not empty: {x}")
        return inputs


class AssertEmptyStep(Assertion, ValidateEmptyStep):
    """
    AssertEmptyStep performs checks against a single observation that should be empty len(x) == 0.
    """
    pass


class RequireEmptyStep(Requirement, ValidateEmptyStep):
    """
    RequireEmptyStep performs checks against a single observation that should be empty len(x) == 0.
    """
    pass


class ValidateNotEmptyStep(ValidateStep):
    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if len(x) == 0:
            self.fail(f"element is empty: {x}")
        return inputs


class AssertNotEmptyStep(Assertion, ValidateNotEmptyStep):
    """
    AssertNotEmptyStep performs checks against a single observation that should not be empty len(x) != 0.
    """
    pass


class RequireNotEmptyStep(Requirement, ValidateNotEmptyStep):
    """
    RequireNotEmptyStep performs checks against a single observation that should not be empty len(x) != 0.
    """
    pass


class ValidateEqualStep(ValidateStep):
    def __init__(self, v: t.Any, **kwargs):
        super().__init__(**kwargs)
        self.v = v

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if x != self.v:
            self.fail(f"elements are not equal: {x} / {self.v}")
        return inputs


class AssertEqualStep(Assertion, ValidateEqualStep):
    """
    AssertEqualStep performs checks against a single observation that should be equals to the value.
    """
    pass


class RequireEqualStep(Requirement, ValidateEqualStep):
    """
    RequireEqualStep performs checks against a single observation that should be equals to the value.
    """
    pass


class ValidateAllInStep(ValidateStep):

    templated: t.Sequence[str] = tuple({"needles"} | set(Step.templated))

    def __init__(self, needles: t.Union[str, t.Sequence[str]], **kwargs):
        super().__init__(**kwargs)
        self.needles = needles

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        if not isinstance(inputs, SequenceMessage):
            raise StepValidationError("ValidateAllInStep requires a sequence to iterate")
        x = inputs.get_value()
        if len(x) == 0:
            self.fail("There is no input data to iterate")
        if len(self.needles) == 0:
            self.fail("There are no needles to iterate")
        for k in self.needles:
            ok = False
            for v in x:
                if k in v:
                    ok = True
                    break
            if not ok:
                self.fail(f"key {k} not in {x}")
        return inputs


class AssertAllInStep(Assertion, ValidateAllInStep):
    """
    AssertAllInStep checks if all items in a list of values is present in a sequence.
    E.g:
    ["a", "b"] all in ["a", "b", "c"] = True
    ["a", "b"] all in ["a", "c", "d"] = False, b is missing
    """
    pass


class RequireAllInStep(Requirement, ValidateAllInStep):
    """
    RequireAllInStep checks if all items in a list of values is present in a sequence.
    E.g:
    ["a", "b"] all in ["a", "b", "c"] = True
    ["a", "b"] all in ["a", "c", "d"] = False, b is missing
    """
    pass


class ValidateGreaterStep(ValidateStep):

    def __init__(self, v: t.Union[int, float], **kwargs):
        super().__init__(**kwargs)
        self.v = v

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if not x:
            self.fail(f"we are expecting a number to compare")
        if not isinstance(x, (int, float)):
            self.fail(f"{x} is not a number")
        if x <= self.v:
            self.fail(f"{x} is not greater than {self.v}")
        return inputs


class AssertGreaterStep(Assertion, ValidateGreaterStep):
    """
    AssertGreaterStep asserts that the input element is greater than the defined value.
    """
    pass


class RequireGreaterStep(Requirement, ValidateGreaterStep):
    """
    RequireGreaterStep asserts that the input element is greater than the defined value.
    """
    pass


class ValidateGreaterOrEqualStep(ValidateStep):

    def __init__(self, v: t.Union[int, float], **kwargs):
        super().__init__(**kwargs)
        self.v = v

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if not x:
            self.fail(f"we are expecting a number to compare")
        if not isinstance(x, (int, float)):
            self.fail(f"{x} is not a number")
        if x < self.v:
            self.fail(f"{x} is not greater than or equal to {self.v}")
        return inputs


class AssertGreaterOrEqualStep(Assertion, ValidateGreaterOrEqualStep):
    """
    AssertGreaterOrEqualStep asserts that the input element is greater than or equal to the defined value.
    """
    pass


class RequireGreaterOrEqualStep(Requirement, ValidateGreaterOrEqualStep):
    """
    RequireGreaterOrEqualStep asserts that the input element is greater than or equal to the defined value.
    """
    pass


class ValidateLessStep(ValidateStep):

    def __init__(self, v: t.Union[int, float], **kwargs):
        super().__init__(**kwargs)
        self.v = v

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if not x:
            self.fail(f"we are expecting a number to compare")
        if not isinstance(x, (int, float)):
            self.fail(f"{x} is not a number")
        if x >= self.v:
            self.fail(f"{x} is not less than {self.v}")
        return inputs


class AssertLessStep(Assertion, ValidateLessStep):
    """
    AssertLessStep asserts that the input element is less than the defined value.
    """
    pass


class RequireLessStep(Requirement, ValidateLessStep):
    """
    RequireLessStep asserts that the input element is less than the defined value.
    """
    pass


class ValidateLessOrEqualStep(ValidateStep):

    def __init__(self, v: t.Union[int, float], **kwargs):
        super().__init__(**kwargs)
        self.v = v

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        x = inputs.get_value()
        if not x:
            self.fail(f"we are expecting a number to compare")
        if not isinstance(x, (int, float)):
            self.fail(f"{x} is not a number")
        if x > self.v:
            self.fail(f"{x} is not less than or equal to {self.v}")
        return inputs


class AssertLessOrEqualStep(Assertion, ValidateLessOrEqualStep):
    """
    AssertLessOrEqualStep asserts that the input element is less than or equal to the defined value.
    """
    pass


class RequireLessOrEqualStep(Requirement, ValidateLessOrEqualStep):
    """
    RequireLessOrEqualStep asserts that the input element is less than or equal to the defined value.
    """
    pass
