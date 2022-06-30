import typing as t
from abc import ABC
from functools import reduce
from itertools import chain

from jmespath import search

from walnut import Step, StepExcecutionError


class MutateStep(Step, ABC):
    """
    MutateSte
    """
    templated: t.Sequence[str] = tuple({"key"} | set(Step.templated))

    def __init__(self, *, key: str = "out", **kwargs):
        super().__init__(**kwargs)
        self.key = key

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)

        if not inputs:
            raise StepExcecutionError(f"{self.__class__.__name__} does not have any input data to mutate")

        return r

    def _get_iterable(self, inputs: t.Any) -> t.Any:
        """
        If _get_iterable is called, verify that inputs can be iterated and return the most simple form of iterable
        """
        if not isinstance(inputs, (t.Iterable, t.Sequence)):
            raise StepExcecutionError(f"Object to mutate using {self.__class__.__name__} is not iterable: {inputs}")
        # If we have a dictionary collapse the values before iterate:
        if isinstance(inputs, dict):
            inputs = list(chain(*inputs.values()))
        return inputs


class SelectStep(MutateStep):
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
    """
    templated: t.Sequence[str] = tuple({"expression"} | set(Step.templated))

    SOURCE_INPUT = "inputs"
    SOURCE_STORE = "store"
    SOURCES = [SOURCE_INPUT, SOURCE_STORE]

    def __init__(self, *, expression: str, inputs: t.Dict[t.Any, t.Any] = None, source: str = SOURCE_INPUT, key: str = "out", **kwargs):
        super().__init__(key=key, **kwargs)
        self.expression = expression
        self.inputs = inputs
        self.source = source if source in self.SOURCES else self.SOURCE_INPUT

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:

        inputs = inputs if self.source == self.SOURCE_INPUT else store
        if not inputs:
            raise StepExcecutionError(f"{self.__class__.__name__}({self.source}) does not have any input data to mutate: {self.expression} ({self.title})")

        r = super().execute(inputs, store)
        r[self.key] = search(self.expression, inputs)
        return r


class FilterStep(MutateStep):
    """
    The filter() function is used to subset a list or dict, retaining all observations that satisfy your conditions.
    To be retained, the item must produce a value of TRUE for all conditions.
    Note that when a condition evaluates to None the item will be dropped.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.FilterStep(fn=lambda x: x >= 5)
    > { "out": [5, 6, 7, 8, 9] }

    """

    def __init__(self, *, fn: t.Callable[[t.Any], bool], key: str = "out", **kwargs):
        super().__init__(key=key, **kwargs)
        self.fn = fn

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        r[self.key] = [v for v in self._get_iterable(inputs) if self.fn(v)]
        return r


class MapStep(MutateStep):
    """
    MapStep creates a new list populated with the results of calling a provided function on every element in the calling attribute.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.MapStep(fn=lambda x: x * 2)
    > { "out": [2, 4, 6, 8, 10, 12, 14, 16, 18]}
    """

    def __init__(self, *, fn: t.Callable[[t.Any], t.Any], key: str = "out", **kwargs):
        super().__init__(key=key, **kwargs)
        self.fn = fn

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        r[self.key] = [self.fn(v) for v in self._get_iterable(inputs)]
        return r


class ReduceStep(MutateStep):
    """
    ReduceStep executes a reducer function on each element of the list and returns a single output value.

    Example:
    > { "n": [1, 2, 3, 4, 5, 6, 7, 8, 9] }
    > walnut.ReduceStep(fn=lambda x, y: x + y)
    > { "out": 45 }
    """
    def __init__(self, *, fn: t.Callable[[t.Any, t.Any], t.Any], key: str = "out", **kwargs):
        super().__init__(key=key, **kwargs)
        self.fn = fn

    def execute(self, inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any]) -> t.Dict[t.Any, t.Any]:
        r = super().execute(inputs, store)
        r[self.key] = reduce(self.fn, self._get_iterable(inputs))
        return r
