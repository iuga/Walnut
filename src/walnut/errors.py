class RecipeExcecutionError(Exception):
    """Raised when there was a problem executing the Recipe"""


class StepExcecutionError(Exception):
    """Raised when there was a problem executing the Step"""


class StepValidationError(Exception):
    """Raised when there is a validation that was unsuccessful"""

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.args[0]}"


class StackableError(Exception):
    """Base of all errors that contain a stacktrace"""

    stack = []

    def add(self, x) -> None:
        self.stack.insert(0, x)

    def __str__(self):
        if len(self.stack) > 0:
            return f"{' ► '.join([c.__class__.__name__ for c in self.stack])} ► {self.__class__.__name__}: {self.args[0]}"
        else:
            return f"{self.__class__.__name__}: {self.args[0]}"


class StepAssertionError(StackableError):
    """
    Raised when there was a assertion that was not evaluated as true.
    This Exception contains a stack to store the path of the nested list of elements.
    We want to be able to identify which was the root cause.
    """


class StepRequirementError(StackableError):
    """
    Raised when there was a requirement that was not evaluated as true
    This Exception contains a stack to store the path of the nested list of elements.
    We want to be able to identify which was the root cause.
    """


class ShortCircuitError(Exception):
    """
    Raised when a Recipe execution must not continue due a ShortCircuitStep.
    """
