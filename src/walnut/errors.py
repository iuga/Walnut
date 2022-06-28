class RecipeExcecutionError(Exception):
    """Raised when there was a problem executing the Recipe"""


class StepExcecutionError(Exception):
    """Raised when there was a problem executing the Step"""


class StepAssertionError(Exception):
    """Raised when there was a assertion that was not evaluated as true"""
