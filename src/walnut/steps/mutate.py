import typing as t
from functools import reduce

from jmespath import search

from walnut import Step
from walnut.errors import StepAssertionError, StepValidationError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.steps.validators import validate_input_type


class SelectStep(Step):
    """
    SelectStep uses JMESPath expession as a query language for the input dictionary.
    For further information please read: https://jmespath.org/specification.html

    Example:
    > expession: a.b.c.d
    > inputs: {"a": {"b": {"c": {"d": "value"}}}}
    > output: "value"

    Overview of selection features
    ------------------------------
    Basic Expressions:
    > a
    > a.b.c.d
    > a[1]
    > a.b.c[0].d[1][0]

    Slicing:
    > [*]
    > [1:5]
    > a[0:5]
    > a[:5]
    > a[::2] # [start:stop:step]
    > [::-1]

    Projections:
    > people[*].first
    > people[:2].first
    > ops.*.numArgs  # object projections
    > reservations[*].instances[*].state  # flatten projections

    Filters:
    > machines[?state=='running'].name

    Multi Select:
    > people[].[name, state.name]
    > people[].{Name: name, State: state.name}

    Pipe Expressions:
    > people[*].first | [0]

    Special Characters:
    > html[0].\"#text\"  # You should escape the key
    """

    templated: t.Sequence[str] = tuple({"expression"} | set(Step.templated))

    SOURCE_INPUT = "inputs"
    SOURCE_STORAGE = "storage"
    SOURCES = [SOURCE_INPUT, SOURCE_STORAGE]

    def __init__(self, expression: str, source: str = SOURCE_INPUT, **kwargs):
        super().__init__(**kwargs)
        self.expression = expression
        self.source = source if source in self.SOURCES else self.SOURCE_INPUT

    @validate_input_type(types=[SequenceMessage, MappingMessage])
    def process(self, inputs: Message) -> Message:
        # Cast the value to Message
        v = (
            inputs
            if self.source == self.SOURCE_INPUT
            else MappingMessage(self.get_storage().as_dict())
        )
        # Validate the message
        if not v:
            raise StepValidationError(
                f"[SelectStep] {self.source} does not have any data to select from: {self.expression}"
            )
        values = inputs.get_value()
        if not values:
            raise StepValidationError(
                f"[SelectStep] {self.source} does not have any data to select from: {self.expression}"
            )
        c = search(self.expression, v.get_value())
        if c is None:
            raise StepAssertionError(
                f"Empty SelectStep('{self.expression}') reading from '{self.source}' the content: {v.get_value()}"
            )
        return c


class FilterStep(Step):
    """
    The filter() function is used to subset a list or dict, retaining all observations that satisfy your conditions.
    To be retained, the item must produce a value of TRUE for all conditions.
    Note that when a condition evaluates to None the item will be dropped.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.FilterStep(fn=lambda x: x >= 5)
    > { "out": [5, 6, 7, 8, 9] }

    """

    def __init__(self, *, fn: t.Callable[[t.Any], bool], **kwargs):
        super().__init__(**kwargs)
        self.fn = fn

    @validate_input_type(types=[SequenceMessage])
    def process(self, inputs: Message) -> Message:
        values = inputs.get_value()
        if not values:
            raise StepValidationError("FilterStep does not have any input data to filter")
        return SequenceMessage([v for v in values if self.fn(v)])


class MapStep(Step):
    """
    MapStep creates a new list populated with the results of calling a provided function on every element in the calling attribute.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.MapStep(fn=lambda x: x * 2)
    > { "out": [2, 4, 6, 8, 10, 12, 14, 16, 18]}
    """

    def __init__(self, fn: t.Callable[[t.Any], t.Any], **kwargs):
        super().__init__(**kwargs)
        self.fn = fn

    @validate_input_type(types=[SequenceMessage])
    def process(self, inputs: Message) -> Message:
        values = inputs.get_value()
        if not values:
            raise StepValidationError("MapStep does not have any input data to filter")
        return SequenceMessage([self.fn(v) for v in values])


class ReduceStep(Step):
    """
    ReduceStep executes a reducer function on each element of the list and returns a single output value.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.ReduceStep(fn=lambda x, y: x + y)
    > { "out": 45 }
    """

    def __init__(self, fn: t.Callable[[t.Any, t.Any], t.Any], key: str = "output", **kwargs):
        super().__init__(key=key, **kwargs)
        self.fn = fn

    @validate_input_type(types=[SequenceMessage])
    def process(self, inputs: Message) -> Message:
        values = inputs.get_value()
        if not values:
            raise StepValidationError("ReduceStep does not have any input data to filter")
        return SequenceMessage(reduce(self.fn, values))
