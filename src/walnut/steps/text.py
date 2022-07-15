import typing as t
import re

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import Message, SequenceMessage, ValueMessage


class TextSubsetStep(Step):
    """
    Keep strings matching a pattern.
    This Step always return a sequence of values, even if the input was a string.
    """
    def __init__(self, pattern: str, **kwargs) -> None:
        """
        :param pattern is the pattern to look for. The default interpretation is a regular expression.
        """
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern)

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        v = inputs.get_value()
        if not isinstance(inputs, (ValueMessage, SequenceMessage)):
            raise StepExcecutionError("TextSubsetStep is expecting a string or sequence of strings")
        if isinstance(inputs, ValueMessage):
            if not isinstance(v, str):
                raise StepExcecutionError(f"TextSubsetStep is expecting a string value, got: {v}")
            v = [v]
        r = []
        for s in v:
            if isinstance(s, str) and self.pattern.search(s):
                r.append(s)
        return SequenceMessage(r)


class TextToCaseStep(Step):
    """
    Convert a string to case.
    """
    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        v = inputs.get_value()
        if isinstance(inputs, SequenceMessage):
            return SequenceMessage([self.to_case(str(s)) for s in v if isinstance(s, str)])
        if isinstance(inputs, ValueMessage) and isinstance(v, str):
            return ValueMessage(self.to_case(str(v)))
        raise StepExcecutionError(f"{self.__class__.__name__} is expecting a string or sequence of strings")

    def to_case(self, s: str) -> str:
        raise NotImplementedError("TextToCaseStep should not be called directly")


class TextToLowerStep(TextToCaseStep):
    """
    Convert a string to lower case.
    """
    def to_case(self, s: str) -> str:
        return s.lower()


class TextToUpperStep(TextToCaseStep):
    """
    Convert a string to upper case.
    """
    def to_case(self, s: str) -> str:
        return s.upper()
