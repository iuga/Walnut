class RecipeExcecutionError(Exception):
    """Raised when there was a problem executing the Recipe"""


class StepExcecutionError(Exception):
    """Raised when there was a problem executing the Step"""


class StepAssertionError(Exception):
    """Raised when there was a assertion that was not evaluated as true"""
    def __str__(self):
        return f"[{self.__class__.__name__}] {self.args[0]}"


class StepRequirementError(Exception):
    """Raised when there was a requirement that was not evaluated as true"""
    def __str__(self):
        return f"[{self.__class__.__name__}] {self.args[0]}"
